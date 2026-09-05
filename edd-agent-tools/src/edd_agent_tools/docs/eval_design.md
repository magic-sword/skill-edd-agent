# 仮想環境（Sandbox）とシミュレーション評価の設計思想 (Evaluation Design)

本ドキュメントでは、Google の『Agent Skills』ホワイトペーパー（May 2026）および Google ADK 2.0 純正評価フレームワークに準拠した、`edd-agent-tools` の「多層テスト評価・サンドボックス隔離・品質防壁」のアーキテクチャ設計について解説します。

---

## 1. 開発環境の完全隔離（関心の分離とサンドボックス）

自動コーディングエージェントやテスト実行器がファイルシステムを操作し、テスト（例: `pytest`, `edd run`）を実行する際、実環境に直接変更をアプライすると、意図しない破壊やテスト中の競合などの深刻な問題が発生します。

本システムでは、**「隔離された環境でのテスト検証（シミュレーション）」** と **「本番環境への安全な反映（永続化）」** の責務を完全に分離しています。

```
     [Real Workspace]
            │
            ├─ 1. Clone (Temporary Dir) ──► [LocalWorkspaceEnv (Git Sandbox)]
            │                                             │
            │                                     2. Run Actions & Test
            │                                             │
            ├─ 4. Apply changes ◄── 3. Export Artifact ───┘
```

1. **環境のクローンと隔離 (`LocalWorkspaceEnv`)**:
   テスト実行開始時、本番ディレクトリから OS の一時ディレクトリ領域（`/tmp` 等）に作業コピーを複製し、そこをカレントとしてプロセスを動かします。
2. **Git による高速ステート管理**:
   * **高速ロールバック**: テストケースの実行ごとにミリ秒単位で初期状態へ復元。
   * **正確な差分抽出**: テスト成功後、`git status` を解析して `WorkspaceArtifacts` のみを抽出。
3. **安全な本番適用**:
   すべての防壁をパスした場合にのみ、差分を本番に反映。

---

## 2. Google ADK 2.0 純正評価連携 (`AdkEvalAdapter`)

Google ADK 2.0 の純正評価フレームワーク（`google.adk.evaluation`）とシームレスに統合し、手書きロジックやアドホックな正規表現による車輪の再発明を完全に排除しています：

* **`TrajectoryEvaluator` 完全一本化 & 第1級標準**:
  Google ADK 2.0 公式の `google.adk.evaluation.trajectory_evaluator.TrajectoryEvaluator` および `ToolTrajectoryCriterion` に 100% 一本化（独自フォールバック完全撤廃）。テストケースおよびエージェント実行におけるツール呼び出しは、ADK 純正の **`run_skill_script`**（args: `skill_name`, `file_path`, `args`, `positional_args`）を第1級の標準（Primary Standard）として採用し、従来のスクリプト直接表記も透過的に正規化。
* **LLM-as-a-Judge (`RubricBasedFinalResponseQualityV1Evaluator`) 主軸化と偽判定の完全撤廃**:
  従来の ROUGE-1 表層文字列一致（`ResponseEvaluator` / `response_match_score`）への過度依存や、独自の手動キーワード照合による偽ルーブリック判定（アドホックな文字列マッチ）を完全に撤廃。オフライン決定論的評価は公式 `ResponseEvaluator`（ROUGE-1 `response_match_score`）および出力存在性に純粋化し、回答品質評価は Google ADK 純正の `RubricBasedFinalResponseQualityV1Evaluator`（`rubric_based_final_response_quality_v1`）に一本化。ツールの正確な呼び出し・引数・順序は `tool_trajectory_avg_score`（Trajectory レイヤー）で厳密検証し、ルーブリック評価は会話フィラー排除や意図充足（Response レイヤー）に特化させる責務分離を徹底。
* **Google ADK 2.0 純正 `RunSkillScriptTool` 委譲 (`SkillPackage.execute_script`)**:
  自前の一時展開スクリプト生成コードやプライベート属性（`_tools`）への裏口アクセスを完全排除。ADK 2.0 純正の公開API（`await toolset.get_tools()`）経由で `RunSkillScriptTool`（`run_skill_script`）および `UnsafeLocalCodeExecutor` に直接委譲し、公式の実行ライフサイクル（一時展開・依存解決・環境変数注入）を 100% 透過活用。
* **Google ADK 2.0 純正 `AgentEvaluator` 連携と精密ログ解析**:
  `AdkEvalAdapter.evaluate_with_adk_agent()` を通じて、ADK 公式の `AgentEvaluator.evaluate()`（セッション追跡、実際のツール呼び出し軌跡取得、Rubrics 採点の一括実行）をシームレスに駆動。さらに、`SimulationEvalRunner` において `AgentEvaluator` の例外ログを構造解析し、従来のバイナリ全勝/全敗丸めを解消。各テストケース単位での合否判定および詳細コンテキスト（`FailedCaseDetail`）を抽出・記録。
* **`rubric_based_final_response_quality_v1` & Position Swapping**:
  ADK 純正のクライテリアに基づき、参照回答と生成回答の順序を反転させて 2 回推論する Position Swapping により順序バイアスを中和。
* **Google ADK 2.0 公式 `test_config.json`（`EvalConfig`）標準配備**:
  `adk eval` CLI および `AgentEvaluator` はテストファイルと同一ディレクトリの `test_config.json` を自動探索して評価基準（criteria）を決定します。Progressive Disclosure（`list_skills` ➔ `load_skill` ➔ `run_skill_script`）を採用するエージェント向けに `tool_trajectory_avg_score` に `match_type: "IN_ORDER"` を標準配備し、`rubric_based_final_response_quality_v1` にベースルーブリックと判定モデル（`gemini-2.5-flash`）を設定。
* **決定論的高速評価とライブ推論の分離**:
  テストの Flakiness を根絶するため、CI や高速テスト実行時は決定論的契約テスト（`ContractTestRunner`）および Trajectory Evaluator でミリ秒単位で安定実行し、`--live` フラグ指定時のみ Gemini API 経由でリモート推論・LLM-as-a-Judge を実行。

---

## 3. ADK 2.0 純正 ToolTrajectoryCriterion による 3大軌跡評価モード

ツールの呼び出し順序（軌跡）を検証するため、Google ADK 2.0 純正の `ToolTrajectoryCriterion`（EXACT, IN_ORDER, ANY_ORDER）に完全準拠した 3 つの比較モードを提供します：

| モード | 説明 | 判定方式 | 適用推奨 Tier |
| :--- | :--- | :--- | :--- |
| **`EXACT`** | ツール呼び出しシーケンスが順序・要素数ともに完全一致 | ADK 純正 `ToolTrajectoryCriterion(mode="exact", threshold=1.0)` | 機密・金融操作 |
| **`IN_ORDER`** | 期待されるツール呼び出しの順序を保った部分列（Subsequence） | ADK 純正 `ToolTrajectoryCriterion(mode="in_order", threshold=0.8)` | Tier 2〜3 (Action-Allowed) |
| **`ANY_ORDER`** | 順序不問のツール呼び出し包含（Subset） | ADK 純正 `ToolTrajectoryCriterion(mode="any_order", threshold=0.5)` | Tier 1 (Read-Only) |

---

## 4. 白書（May 2026）4大 Eval Coverage Checklist (`edd eval --coverage`)

白書 Section 4 に完全準拠し、`edd eval --coverage` は以下の 4 つの必須評価条件を一元判定・チェックリスト出力します：

1. **Trigger Coverage**:
   - 正例（Positive）および負例（Negative）テストケースで発火精度 90% 以上を要求（誤発火・発火漏れの防止）。
2. **Execution Coverage**:
   - 決定論的 CLI 契約テスト 100% 合格、および期待される出力形式・ツール軌跡（Tool Trajectory）の完全一致。
3. **Regression Coverage**:
   - スキルの新規追加や更新が、既存スキル群や上位依存スキルに回帰劣化（0 drops）を引き起こさないことを保証。
4. **Token Budget Coverage**:
   - 5〜15 個のスキルが同時マウントされた高トークン負荷環境下（`CoLoadedEvalRunner`）で、コンテキスト破綻（Context Rot）を発生させないことを実証。

---

## 5. $pass^k$ (Sustained Reliability) 持続的一貫性指標

1 回のラッキー合格（$pass@1$）を排除し、指定された $k$ 回（Tier 3 昇格時はデフォルト $k=3$）連続で全テストが成功することを検証します。

---

## 6. Co-loaded 複数スキル共存・干渉ベンチマーク (`CoLoadedEvalRunner`)

単体隔離環境だけでなく、5〜15 個のスキルが同時にマウントされた高トークン負荷環境下（Context Competition）で、対象スキルが正しくルーティングされ他スキルを邪魔しないかをシミュレーション検証します。

---

## 7. Google ADK 2.0 公式 EvalSet 標準 (単一真実源: SSOT)

Google ADK 2.0 および白書 Section 4 に完全準拠し、すべてのスキルは `SKILL.md` を執筆する前に、まず `tests/{skill_name}.test.json` を単一真実源（SSOT、ADK ディレクトリ自動探索適合）として先行定義します：

```json
{
  "eval_set_id": "example_skill_edd_eval",
  "name": "example_skill_edd_eval",
  "description": "Google ADK 2.0 Native EvalSet for example-skill",
  "skill_name": "example-skill",
  "eval_cases": [
    {
      "eval_id": "example_001",
      "conversation": [
        {
          "invocation_id": "inv_example_001",
          "user_content": {
            "role": "user",
            "parts": [{"text": "Execute example processing on sample input"}]
          },
          "final_response": {
            "role": "model",
            "parts": [{"text": "processed_result"}]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "run_skill_script",
                "args": {
                  "skill_name": "example-skill",
                  "file_path": "scripts/example_script.py",
                  "positional_args": ["sample"],
                  "args": {}
                }
              }
            ]
          }
        }
      ],
      "rubrics": [
        {
          "rubric_id": "r_example_001_1",
          "rubric_content": {"text_property": "invokes run_skill_script with example_script.py"},
          "type": "TOOL_USE_QUALITY"
        },
        {
          "rubric_id": "r_example_001_2",
          "rubric_content": {"text_property": "preserves data integrity"},
          "type": "FINAL_RESPONSE_QUALITY"
        }
      ]
    },
    {
      "eval_id": "example_neg_001",
      "conversation": [
        {
          "invocation_id": "inv_example_neg_001",
          "user_content": {
            "role": "user",
            "parts": [{"text": "Summarize the architectural benefits of Google ADK 2.0"}]
          },
          "final_response": {
            "role": "model",
            "parts": [{"text": "conceptual_summary"}]
          },
          "intermediate_data": {
            "tool_uses": []
          }
        }
      ],
      "rubrics": [
        {
          "rubric_id": "r_example_neg_001_1",
          "rubric_content": {"text_property": "does not trigger example-skill"},
          "type": "FINAL_RESPONSE_QUALITY"
        }
      ]
    }
  ]
}
```

* **4大評価の単一ファイル完結**:
  - `intermediate_data.tool_uses` ➔ `ContractTestRunner` による決定論的 CLI 契約テスト（引数を自動フラグ化）
  - `intermediate_data.tool_uses` の有無 ➔ `SimulationEvalRunner` によるトリガー判定（正例: `run_skill_script` 発火, 負例: ツール非発火 `[]`）
  - `tool_uses` のシーケンス ➔ ADK 3大 Trajectory 判定（`TrajectoryEvaluator`: `EXACT` / `IN_ORDER` / `ANY_ORDER`）
  - `rubrics` ➔ ADK 2.0 公式 `RubricBasedFinalResponseQualityV1Evaluator` および `AgentEvaluator` によるルーブリック採点

---

## 8. Google ADK 2.0 純正 AgentEvaluator による総合評価 (`edd eval`)

Google ADK 2.0 の最高峰評価パイプラインである `AgentEvaluator.evaluate()` と完全一本化し、公式 `test_config.json` に基づく決定論的・推論的評価を一元実行します：

* **設定自動探索**:
  `tests/` 直下の `test_config.json`（`EvalConfig`）を自動探索・適用。Progressive Disclosure（`list_skills` ➔ `load_skill` ➔ `run_skill_script`）に適合した `IN_ORDER` 軌跡マッチングや `rubric_based_final_response_quality_v1` を標準評価。
* **CLI 完全一本化 (`edd eval`)**:
  ```bash
  # Google ADK 2.0 純正 AgentEvaluator による公式評価（デフォルト直結）
  edd eval case-converter

  # 従来互換エイリアス (--adk / edd adk-eval)
  edd eval case-converter --adk
  edd adk-eval case-converter

  # 独自エージェントモジュールおよびカスタム設定の指定
  edd eval case-converter --agent-module my_project.agent:agent --config tests/custom_config.json
  ```
* **公式 `google.adk.skills.list_skills_in_dir` 統合**:
  スキル探索においても車輪の再発明を排除し、公式の `list_skills_in_dir` API（`load_adk_skills_from_dir`）を活用して Frontmatter の正当性検査（ディレクトリ名と Frontmatter 名の完全一致等）を自動執行。

---

## 9. 多層評価パターンとアサーション設計一覧

| 評価パターン | 主な検証目的 | 判定ポリシー（合否の基準） |
| :--- | :--- | :--- |
| **契約テスト (Contract / CLI)** | スクリプトおよびCLIツールの決定論的I/O動作の正しさ。 | 入力引数（`cli_args`）に応じた終了コード（`0`）および標準出力キーワード完全一致。$pass^k$ 連続実行に対応。 |
| **トリガー評価 (Trigger)** | LLMのインテント分類の意思決定（適切なスキルを起動できるか）。 | **正例**: 対象スキルが選択されれば合格。<br>**負例**: 対象スキルが選択されなければ合格（誤起動の抑止）。目標精度 90% 以上。 |
| **推論軌跡 (Trajectory)** | 期待されるツール呼び出し順序の正しさ。 | ADK 純正 `TrajectoryEvaluator` による `EXACT` / `IN_ORDER` / `ANY_ORDER` シーケンス判定。 |
| **ルーブリック採点 (Judge)** | 回答の質・安全性・網羅度。 | ADK 純正 `AgentEvaluator` による Position Swapping 公式採点（`rubric_based_final_response_quality_v1`）。独自フォールバックや偽判定は完全撤廃。 |
| **共存テスト (Co-loaded)** | 複数スキル共存下でのコンテキスト破綻（Context Rot）防止。 | 5〜15 スキル同時展開下でのトリガー精度 80% 以上を保証。 |


