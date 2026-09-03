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

Google ADK 2.0 の純正評価フレームワーク（`google.adk.evaluation`）とシームレスに統合し、手書きロジックによる車輪の再発明を完全に排除しています：

* **`TrajectoryEvaluator` 直接駆動 & 第1級標準**:
  Google ADK 2.0 公式の `google.adk.evaluation.trajectory_evaluator.TrajectoryEvaluator` および `ToolTrajectoryCriterion` を直接駆動。テストケースおよびエージェント実行におけるツール呼び出しは、ADK 純正の **`run_skill_script`**（args: `skill_name`, `file_path`, `args`）を第1級の標準（Primary Standard）として採用し、従来のスクリプト直接表記（`scripts/xxx.py`）も透過的に正規化。
* **Google ADK 2.0 純正 `AgentEvaluator` 連携**:
  `AdkEvalAdapter.evaluate_with_adk_agent()` を通じて、ADK 公式の `AgentEvaluator.evaluate()`（セッション追跡、実際のツール呼び出し軌跡取得、Rubrics 採点の一括実行）をシームレスに駆動。
* **`rubric_based_final_response_quality_v1` & Position Swapping**:
  ADK 純正のクライテリアに基づき、参照回答と生成回答の順序を反転させて 2 回推論する Position Swapping により順序バイアスを中和。
* **決定論的高速評価とライブ推論の分離**:
  テストの Flakiness を根絶するため、通常テスト・CI は決定論的フォールバック（ミリ秒単位）で安定実行し、`--live` フラグ指定時のみ Vertex AI / Gemini API 経由でリモート推論を実行。

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

## 7. 白書標準 EDD (Evaluation-Driven Development) Snippet 3 形式 (SSOT)

白書 Section 4 に完全準拠し、すべてのスキルは `SKILL.md` を執筆する前に、まず `tests/{skill_name}_edd.evalset.json` を単一真実源（SSOT）として先行定義します：

```json
{
  "eval_set_id": "example_skill_edd_eval",
  "skill_name": "example-skill",
  "cases": [
    {
      "case_id": "example_001",
      "input": "Execute example processing on sample input",
      "expected_skill": "example-skill",
      "expected_tool_calls": [
        {"tool": "scripts/example_script.py", "args": {"input": "sample"}}
      ],
      "expected_output_format": "processed_result",
      "rubric": [
        "invokes scripts/example_script.py CLI tool",
        "preserves data integrity"
      ]
    },
    {
      "case_id": "example_neg_001",
      "input": "Summarize the architectural benefits of Google ADK 2.0",
      "expected_skill": null,
      "expected_tool_calls": [],
      "expected_output_format": "conceptual_summary",
      "rubric": [
        "does not trigger example-skill",
        "answers user query directly without tool calls"
      ]
    }
  ]
}
```

* **4大評価の単一ファイル完結**:
  - `expected_tool_calls` ➔ `ContractTestRunner` による決定論的 CLI 契約テスト（`args` を自動フラグ化）
  - `expected_skill` ➔ `SimulationEvalRunner` によるトリガー判定（正例・負例）
  - `expected_tool_calls` のシーケンス ➔ ADK 3大 Trajectory 判定（`EXACT` / `IN_ORDER` / `ANY_ORDER`）
  - `rubric` ➔ ADK 2.0 `AgentEvaluator` による Position Swapping ルーブリック採点

---

## 7. 多層評価パターンとアサーション設計一覧

| 評価パターン | 主な検証目的 | 判定ポリシー（合否の基準） |
| :--- | :--- | :--- |
| **契約テスト (Contract / CLI)** | スクリプトおよびCLIツールの決定論的I/O動作の正しさ。 | 入力引数（`cli_args`）に応じた終了コード（`0`）および標準出力キーワード完全一致。$pass^k$ 連続実行に対応。 |
| **トリガー評価 (Trigger)** | LLMのインテント分類の意思決定（適切なスキルを起動できるか）。 | **正例**: 対象スキルが選択されれば合格。<br>**負例**: 対象スキルが選択されなければ合格（誤起動の抑止）。目標精度 90% 以上。 |
| **推論軌跡 (Trajectory)** | 期待されるツール呼び出し順序の正しさ。 | `EXACT` / `IN_ORDER` / `ANY_ORDER` に従ったシーケンス判定。 |
| **ルーブリック採点 (Judge)** | 回答の質・安全性・網羅度。 | ADK 純正 `AgentEvaluator` または決定論的フォールバックによる Position Swapping 採点。 |
| **共存テスト (Co-loaded)** | 複数スキル共存下でのコンテキスト破綻（Context Rot）防止。 | 5〜15 スキル同時展開下でのトリガー精度 80% 以上を保証。 |

