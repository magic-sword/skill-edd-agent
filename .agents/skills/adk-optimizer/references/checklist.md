# Google ADK 2.0 準拠性チェックリスト (Audit Checklist)

本チェックリストは、本プロジェクトが Google ADK 2.0 の公式ベストプラクティスに厳格に準拠しているかを評価するための単一真実源（SSOT）です。

---

## 1. Code Execution (スクリプト実行基盤)
- [ ] **公式 Code Executor の直接利用**:
  - `google.adk.code_executors.BaseCodeExecutor` を継承した実行エンジン（例: `LocalSubprocessCodeExecutor`）を使用しているか。
  - 自前の脆弱な `subprocess.run` 直叩きやラッパースクリプト生成（車輪の再発明）を行っていないか。
- [ ] **内部非公開クラスの完全排除**:
  - `_SkillScriptCodeExecutor` などの内部クラスやプライベート属性（`_tools` 等）への裏口アクセスが存在しないか。
- [ ] **公式引数仕様への厳格準拠**:
  - スクリプト引数の組み立てが ADK 2.0 公式の `build_script_argv` 仕様（`args`, `short_options`, `positional_args`）に準拠しているか。
- [ ] **実行コンテキストスキーマ**:
  - ADK 2.0 Pydantic スキーマ（`Session.id`, `app_name`, `user_id`）に適合しているか。

---

## 2. Skill Management & Progressive Disclosure (スキル管理)
- [ ] **公式 Toolset の活用**:
  - `google.adk.skills.SkillToolset` を基盤とし、Progressive Disclosure ライフサイクル（`list_skills` ➔ `load_skill` ➔ `run_skill_script` / `load_skill_resource`）に完全準拠しているか。
- [ ] **二重定義・プロンプトハードコードの排除**:
  - システムプロンプトにスキル一覧や手順を静的にベタ書きしていないか（`DEFAULT_SKILL_SYSTEM_INSTRUCTION` と重複させず、動的探索に委ねているか）。
- [ ] **Frontmatter 仕様の完全一致**:
  - `name` とディレクトリ名が `kebab-case` で完全一致しているか。
  - `allowed-tools` がスペース区切り文字列になっているか。
  - 独自拡張プロパティ（`pattern`, `tier` 等）が `metadata:` 辞書配下に格納され、ADK 2.0 `_ALLOWED_FRONTMATTER_KEYS` に準拠しているか。
- [ ] **Don't reinvent MCP as scripts**:
  - 外部 API 連携（GitHub, Slack 等）をスクリプト内で巨大な HTTP クライアントとして再発明していないか（MCP ツールへ委譲されているか）。

---

## 3. Evaluation & Quality Guardrails (評価基盤)
- [ ] **ADK 2.0 公式 Evaluator の直接駆動**:
  - 独自の手動キーワード照合や独自正規表現による「偽ルーブリック判定」を完全排除しているか。
  - 軌跡評価に `google.adk.evaluation.trajectory_evaluator.TrajectoryEvaluator`（`tool_trajectory_avg_score`）および型安全な `ToolTrajectoryCriterion` を使用しているか。
  - LLM-as-a-Judge に `RubricBasedFinalResponseQualityV1Evaluator`（`rubric_based_final_response_quality_v1`）を採用しているか。
- [ ] **責務分離の原則 (Responsibility Separation)**:
  - ツール呼び出し・引数（`positional_args` / `args`）の検証は Trajectory レイヤー（`intermediate_data.tool_uses`）に集約されているか。
  - ルーブリック評価はエージェントの最終回答品質（簡潔性、フィラー排除、負例対応）に特化しているか。
- [ ] **テスト設定（EvalConfig）**:
  - `test_config.json` で Progressive Disclosure のために `match_type: "IN_ORDER"` を標準指定しているか。

---

## 4. Agent Architecture & App Lifecycle (エージェント構成)
- [ ] **App コンテナ配備**:
  - `src/agent.py` に公式 CLI（`adk run`, `adk web`）互換の `App` コンテナ（`app = App(name=..., root_agent=root_agent)`）が配備されているか。
- [ ] **Code Executor の直接注入**:
  - 推奨パターンに従い、エージェント生成時に `code_executor=code_executor` を直接注入しているか。
- [ ] **ライフサイクルコールバック**:
  - `before_agent_callback` や `after_agent_callback` を活用し、アドホックな前処理・後処理フックを排除しているか。

---

## 5. 削除・清掃対象アンチパターン (Dead Code & Legacy Debt)
- [ ] 未使用の後方互換性関数、旧ADK 1.x 向けフォールバック分岐の残存
- [ ] 古い設計思想（非推奨の `examples/` ディレクトリ探索、旧フォーマット等）の残存
- [ ] ドキュメント（`design_philosophy.md`, `AGENTS.md`, `README.md`）内の古い仕様記述
