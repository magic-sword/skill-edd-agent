# Agent Skill 設計思想 (Design Philosophy)

本プロジェクトにおける Google ADK 2.0 および Anthropic 標準（Markdown-First & Progressive Disclosure）スキルの設計思想とベストプラクティスを記録します。
Google 『Agent Skills』ホワイトペーパー（May 2026）に完全準拠した最新の評価・品質防壁アーキテクチャを採用しています。

---

## 0. プロジェクトの目的と設計哲学 (Project Vision & Core Purpose)

### 🎯 プロジェクトの北極星 (North Star)
本プロジェクトの究極の目的は、**「AI エージェントが自らのスキル（手順書・ドメイン知識・決定論的スクリプト）を自律的にテスト・診断・修復・進化させる自己進化システム（Self-Evolving Agentic Ecosystem）」** の構築です。

### ⚖️ 最重要トレードオフの原則 (The Core Trade-off)
一般的なソフトウェア開発では「DRY原則（重複排除・共通ライブラリ化）」が重視されますが、本プロジェクトでは **「自己改善の局所性（Locality of Mutation）と安全な隔離（Isolation）」を DRY原則よりも上位の原則** として優先します。

* **なぜパッケージに個別処理を集約してはならないのか？**:
  1. **探索空間の極小化 (Search Space Localization)**: エージェントがバグを修正したり性能を改善する際、変更対象が `skills/<skill-name>/` 内に閉じていれば、迷走せず迅速・正確に修正を完了できます。
  2. **爆発半径の極小化 (Blast Radius Minimization)**: スキル内のスクリプトが自己改善の試行錯誤で一時的に壊れても、共通パッケージや他のスキルを巻き込んでシステム全体が停止するリスクをゼロにします。
  3. **サンドボックス評価の容易性 (Safe Sandboxing & Rollback)**: スキルが単一ディレクトリで完結しているため、仮想環境（`LocalWorkspaceEnv`）に安全に複製して何度でもテスト・評価・ロールバックが可能です。
  4. **ポータビリティの保証 (Drop-in Portability)**: スキルが外部パッケージに直接 Python import 依存しないことで、Claude Code, Antigravity, Cursor, Google ADK 等のあらゆる環境へ zip 1つで即座に配布・利用できます。

* **スキルの依存関係（Prerequisites / Requirements）に関する標準方針**:
  - **メタスキル（`skill-creator`, `skill-evolver`）**: `pytest` が `pytest` を前提とするのと同様、**`pip install edd-agent-tools` を前提とし、統合 CLI `edd` を直接呼び出す手順書（CLI-as-an-API）** です。不要な薄型ラッパースクリプトを排除し、単一真実源（SSOT）と保守性を最大化します。
  - **一般ドメインスキル（業務・ツールスキル）**:
    - 軽量ユーティリティ（例: `case-converter`, `secret-sanitizer`）は Python 標準ライブラリのみで完結させます。
    - 外部ライブラリ依存（例: `docx`, `xlsx`, `playwright` 等）が必要なスキルは、Anthropic 公式標準に従い `SKILL.md` の `## Requirements & Prerequisites` に必要な pip パッケージを明記します（環境構築されている前提で実行）。`SkillValidator` が AST 解析により記述漏れを自動検知します。

---

## 1. コア思想とアーキテクチャ原則

### ① Two-Tier Architecture（不変プラットフォーム vs 自己改善資産）
* **不変プラットフォーム層 (`edd-agent-tools`)**:
  - スキルのスキーマ検証（`SkillValidator`）、サンドボックス実行（`LocalWorkspaceEnv`）、多層評価（`ContractTestRunner`, `SimulationEvalRunner`, `AdkEvalAdapter`, `CoLoadedEvalRunner`）、Tier状態管理（`SkillsState`）、ZIPパッケージャなどの決定論的インフラを提供。
  - プロンプト文体や生成ロジックをコード内に過度にハードコードしない。
* **自己改善スキル資産層 (`src/skills/`)**:
  - スキル作成用の Markdown テンプレート素材、プロンプト定義（`SKILL.md`）、決定論的スクリプト（`scripts/`）、契約テスト（`tests/`）を集約。
  - エージェントが自己改善（プロンプト進化）する際、pip パッケージのコードを変更することなく安全に進化可能。

### ② 単一真実源とカスケード解決 (Cascading Template Resolver)
* 仕様書兼プロンプトである **`SKILL.md` を唯一の真実源** とし、自然言語（Markdown）とコード（Python）のシームレスな統合を図ります。
* テンプレート解決は **カスケード解決機構（Cascading Template Resolver）** を採用：
  1. ワークスペース側の自己改善テンプレート（`skills/skill-creator/assets/templates/`）を最優先で探索
  2. 存在しない場合はパッケージ組み込みテンプレート（`edd_agent_tools.packaging.templates`）へ安全にフォールバック

### ③ Progressive Disclosure（段階的情報開示とリソース分離）
* コンテキストウィンドウの効率化と信頼性の両立を図るため、スキル資産を明確な3階層に分離します：
  1. **Level 1: YAML Frontmatter**（常時ロード: `name`, `description`）
     - **Routing Algorithm**: `description` はエージェントがスキルを発動するかを判断する唯一のルーティング指標。**動詞起点（Verb-led sentence）** で開始し、「Use when...（発動条件）」および「Do NOT use for...（除外条件）」を明記し、トリガーキーワードを前方に集める（Front-load keywords）。
  2. **Level 2: SKILL.md 本文**（トリガー時ロード: 意思決定ツリー、手順、ガイドライン、When NOT to use）
     - **Context Rot 対策**: 本文は 5,000 words（約 15,000 文字）以内に抑え、詳細な仕様やエッジケースは `references/` に分離。
     - **Give the reason, not just the rule**: `ALWAYS` や `NEVER` などの大文字命令を詰め込む Context Debt を避け、設計理由と客観的指示（Imperative form: "To accomplish X, do Y"）を記述。
  3. **Level 3: Bundled Resources**（オンデマンド実行・ロード）
     - `scripts/`: 決定論的Python/Bashスクリプト（Zero-dependency, CLI `--help` 対応, Black-box 実行）。**Shift Intelligence Left** により、モデルの推論プロンプトから決定論的処理をコードへオフロード。
     - `references/`: ドメイン知識・API仕様・スキーマ（オンデマンド読み込み）
     - `assets/`: 出力用テンプレート・素材（成果物への流用・コピー用）
### ④ Google ADK 2.0 純正フレームワーク完全統合 (`google.adk.skills`, `SkillToolset`, `SkillRegistry`, `LocalCodeExecutor`, `TrajectoryEvaluator`, `ResponseEvaluator`, `EvalConfig`)
* Google ADK 2.0 純正の `SkillToolset` による Progressive Disclosure ライフサイクル（`list_skills` ➔ `load_skill` ➔ `load_skill_resource` ➔ `run_skill_script` ➔ `search_skills`）を完全採用。
* **Progressive Disclosure の動的解決アーキテクチャ**:
  - `EddSkillToolset` は起動時にシステム必須のメタスキル（`skill-creator`, `skill-evolver`）のみをプリロードし、一般ドメインスキル（`case-converter`, `secret-sanitizer` 等）は `EddSkillRegistry` に登録。エージェントは `search_skills` ツールで動的にスキルを探索し、`load_skill` ツールでオンデマンドに instructions や resources をロードします。
* **モンキーパッチおよび車輪の再発明の完全排除**:
  - ADK 内部メソッドの上書き（monkey patch）や不要な同期ラッパー（`*_sync`）、一時的な Toolset 生成によるプライベート属性アクセス（`_tools`）の裏口ハックを全廃し、ADK 公式の非同期ツールセットおよび `google.adk.code_executors.UnsafeLocalCodeExecutor` を標準注入。決定論的スクリプト実行はドメイン層の `SkillPackage.execute_script` または ADK 純正 `run_skill_script` ツールに一本化。
  - 軌跡比較ロジックおよび独自Judge正規表現ルールの再発明を完全排除し、ADK 2.0 純正の `google.adk.evaluation.trajectory_evaluator.TrajectoryEvaluator`（`tool_trajectory_avg_score`）および `google.adk.evaluation.response_evaluator.ResponseEvaluator`（ROUGE-1 `response_match_score`）を直接駆動。
  - **型安全な公式専用 Criterion の採用**: `ToolTrajectoryCriterion(threshold=..., match_type=...)` および `RubricsBasedCriterion(rubrics=..., threshold=...)` を直接インスタンス化し、汎用基底クラスへの押し込みを排除。
  - **Tool Trajectory の第1級標準 (Primary Standard)**: テストケースおよびエージェント実行におけるツール呼び出しは、ADK 2.0 純正の `run_skill_script`（args: `skill_name`, `file_path`, `args`, `positional_args`）を第1級の標準（Primary Standard）として採用。
  - **Google ADK 2.0 公式 `test_config.json`（`EvalConfig`）の標準配備**:
    各スキルの `tests/test_config.json` にて `tool_trajectory_avg_score` に `match_type: "IN_ORDER"` を標準指定。これにより、Progressive Disclosure（`list_skills` ➔ `load_skill` ➔ `run_skill_script`）を採用するエージェントが不当に Fail 判定されないよう保証。また、`rubric_based_final_response_quality_v1`（LLM-as-a-Judge 評価）を標準設定。
  - **Frontmatter 公式仕様の完全一致**: `allowed-tools` は ADK 2.0 および agentskills.io 公式仕様に基づきスペース区切り文字列（例: `"run_skill_script load_skill_resource"`）として正規化し、`metadata.adk_additional_tools` による追加ツール公開に対応。
* `AdkEvalAdapter` により、ADK 純正の `AgentEvaluator` および Rubrics-based Criteria（`rubric_based_final_response_quality_v1` 等）を透過接続。
* 評価の順序バイアスを中和する **Position Swapping**（参照と実回答を入れ替えて2回推論し相加平均）を標準装備。
* **Don't reinvent MCP as scripts (MCP再発明の禁止)**: 白書 Appendix A 準拠。外部API（GitHub, Slack, Salesforce等）との接続や外部データ取得は MCP ツールに委譲し、スキルスクリプト内で巨大な HTTP クライアントを再発明してはならない。スキルは Know-how（決定論的手順と処理）に集中する。


### ⑤ 3大 Tool Trajectory 評価モード (Google ADK 2.0 TrajectoryEvaluator 準拠)
* 出力結果だけでなく、ツールの呼び出し順序（Tool Trajectory）を ADK 2.0 純正の `TrajectoryEvaluator` で検証：
  - **`EXACT`**: 順序・要素数が完全一致
  - **`IN_ORDER`**: 期待される順序を保った部分列（Action-Allowed Tier 3 用）
  - **`ANY_ORDER`**: 順序不問の包含関係（Read-Only Tier 1 用）

### ⑥ $pass^k$ (Sustained Reliability) & 白書 4大 Eval Coverage 検証
* 1 回のラッキー合格（$pass@1$）を排除し、指定された $k$ 回連続実行で全勝を要求する **$pass^k$ 指標** を導入。
* 白書（May 2026）Section 4 の **4大 Eval Coverage Checklist** を `edd eval --coverage` で一元検証：
  1. **Trigger Coverage**: 正例・負例テストケースで 90% 以上の発火精度
  2. **Execution Coverage**: 期待される出力およびツール軌跡（Tool Trajectory）の完全一致
  3. **Regression Coverage**: 既存スキル群に対する連鎖回帰の劣化ゼロ
  4. **Token Budget Coverage**: 5〜15 スキルが同時マウントされた高トークン負荷環境下での Context Rot 防止（`CoLoadedEvalRunner`）

### ⑦ 白書標準 EDD (Evaluation-Driven Development) インバージョン開発と ADK 2.0 公式 EvalSet
* `SKILL.md` を書き始める前に、まず Google ADK 2.0 公式 `EvalSet` スキーマ（`eval_set_id`, `eval_cases`, `conversation`, `Invocation`, `intermediate_data.tool_uses`, `rubrics`）による 3つの正例 ＋ 3つの負例（計6ケース、白書 Section 4 Page 22 必須要件）を策定する「インバージョン開発」を徹底。
* 期待されるツール呼び出し軌跡（`run_skill_script` を標準とする Tool Trajectory）と公式ルーブリック（`rubrics`）を先に定義することで、スキルの機能仕様と境界が明確化され、ハルシネーションや誤発火を未然に防止。独自スキーマによるデータ二重管理を排し、Google ADK 公式 CLI `adk eval` や `AgentEvaluator` とそのまま直結動作します。

### ⑧ 4段階品質保証パイプライン (The Read / Draft / Act Ladder)
* **Tier 1 (`READ_ONLY`)**: 静的検証（`edd validate` 警告/エラー0）+ CLI契約テスト（100%合格）+ トリガー精度（90%以上）
* **Tier 2 (`DRAFT_ONLY`)**: ゴールデンデータセット評価（90%以上）+ 連鎖回帰テスト（Cascade Regression 100%パス）
* **Tier 3 (`ACTION_ALLOWED`)**: Trajectory 評価（`IN_ORDER` / `EXACT`）+ $pass^k$ 持続的一貫性（$k \ge 3$）+ Co-loaded 共存テスト + **人間の明示的承認（Human Sign-off: `--yes`）**

---

## 2. スキル品質の 5 大原則 (The Five Quality Principles)

1. **One Skill, One Job**: 1文で説明できないスキルは分割する。不要な「and」で無関係な機能を束ねない。
2. **Descriptions are an Interface**: Description はルーティングアルゴリズム。曖昧な説明文は未発動（Under-trigger）または誤爆（Over-trigger）の原因。
3. **Shift Intelligence Left**: 実行時に LLM のプロンプトで複雑なルールを守らせるのではなく、テスト可能なスクリプトや明確なスキーマにロジックを落とし込む。
4. **Context is a Budget, Not a Vessel**: コンテキスト容量が 1M トークンあっても、50K トークンを超えると精度劣化（Context Rot / Lost in the Middle）が発生する。不要な情報を常に削ぎ落とす。
5. **Treat Skills as Code**: スキルは依存ライブラリと同様にバージョン管理・テスト・PRレビューを行う。テストのないスキルは機能ではなく単なる期待に過ぎない。

---

## 3. システム・アーキテクチャのレイヤード構造

```
edd_agent_tools/
├── core/           # 共通ドメインエンティティ (SkillPackage, SkillTests)
├── state.py        # 状態管理・探索・DAG解析 (SkillsState)
├── models/         # データモデル (SkillSpec, SkillTier, EvalSet/EvalCase, EvalRunResult)
├── validation/     # 汎用静的リンター (SkillValidator - AST解析, Prerequisites照合, 白書命名規則検査)
├── packaging/      # ZIP パッケージャ (SkillPackager), スキャフォールド (SkillScaffolder, Cascading Resolver)
├── evaluation/     # 契約テスト (ContractTestRunner), シミュレーション (SimulationEvalRunner), ADK連携 (AdkEvalAdapter, ToolTrajectoryCriterion, RubricsBasedCriterion), 共存テスト (CoLoadedEvalRunner), 診断 (SkillDiagnoser), 最適化 (SkillOptimizer), サンドボックス (LocalWorkspaceEnv)
├── adk/            # Google ADK 2.0 連携 (create_adk_skill_toolset, EddSkillToolset, EddSkillRegistry, UnsafeLocalCodeExecutor)
├── mcp/            # FastMCP サーバー (edd-agent-mcp)
└── cli.py          # 統合 CLI (edd run/init/validate/package/eval/tier-gate/diagnose/optimize/list)
```

---

## 4. スキルフォルダ構造および命名規約 (Standard Layout & Appendix A Naming)

Google ADK 2.0 公式ランタイム制約および白書標準（Appendix A & Section 4）に完全準拠したディレクトリ構造と命名規則を採用します：

* **Directory Name & Skill Name (Frontmatter)**: **`kebab-case`（例: `case-converter`, `secret-sanitizer`）**
  - **重要**: Google ADK 2.0 公式ランタイム（`load_skill_from_dir`）は、内部で `skill_dir.name == frontmatter.name`（完全一致）を必須バリデーションとしてアサートしています。そのため、ディレクトリ名とスキル名は必ず一致させて配置します（Anthropic 公式 `awesome-claude-skills` も同規約）。
  - なお、白書 Appendix A で言及される `snake_case` ディレクトリ名（例: `case_converter`）が万一指定された場合でも、`edd` ランタイム（`SkillsState`, `cli`）は双方向で透過的に自動解決する耐障害性を備えています。
* **Script Name**: **`snake_case`（例: `case_converter.py`）** - Python のモジュール・スクリプト標準。
* **動名詞の推奨 (Prefer gerund form)**: 名詞（`pdf-processor`）より動名詞（`processing-pdfs`）を推奨。
* **ベンダープレフィックスおよび汎用名の排除**: `gemini-*`, `claude-*` や `utils`, `tools` などの曖昧な命名を禁止。
* **評価データセット単一真実源 (SSOT) と責務分離**: 乱立する複数のテストファイルを廃止し、Google ADK 2.0 公式 `EvalSet` スキーマ（`eval_set_id`, `eval_cases`, `conversation`, `intermediate_data.tool_uses`, `rubrics`）の **`{skill_name}_edd.evalset.json`（正例 3 件＋負例 3 件の計6件、白書 Section 4 Page 22 必須要件）に一元化**。
  - **責務分離の原則 (Responsibility Separation)**: ツール呼び出し・引数・順序の検証は `expected_tool_calls` / `intermediate_data.tool_uses`（Trajectory レイヤー）に集約し、`rubric` はエージェントの最終出力品質（正確性・簡潔性・会話フィラーの排除・負例時の適切な振る舞い）に特化させる。

---

## 5. 白書 Appendix A minimal SKILL.md 6大必須セクション仕様

すべての `SKILL.md` は、白書 Appendix A が定める以下の 6 つの必須セクションを標準レイアウトとして実装します：

1. **`## When to use`**: 具体的なトリガー条件、発話キーワード、適用シナリオ。
2. **`## When NOT to use`**: 粒度境界・技術的限界・ライフサイクル分離・インベントリ照合に基づく明確な除外条件。
3. **`## Workflow`**: 決定論的ステップ手順と CLI 実行コマンド。
4. **`## Examples`**: 入力発話と期待出力の具体例（Few-shot ガイダンス）。
5. **`## Output format`**: 成果物仕様、ファイル配置、回答形式。
6. **`## Anti-patterns to avoid`**: コンテキスト浪費や破壊的変更を防ぐための注意事項。

```
src/skills/{skill_name}/
  SKILL.md       # YAML Frontmatter (動詞起点 + Use when + Do NOT use) + 白書 6大必須セクション (SSOT)
  scripts/       # 決定論的スクリプト（Python標準 snake_case、CLI --help 対応、Zero-dependency、ドメイン処理がある場合のみ）
    {primary_script}.py
  references/    # ドメイン知識・仕様・スキーマ（オンデマンド参照）
    guide.md
  assets/        # 出力用テンプレート・素材（成果物への流用・コピー用）
    sample.txt
  examples/      # 具象コード例・パターン集（エージェントが真似できる実装例）
    example_usage.py
  tests/         # Google ADK 2.0 公式 EvalSet 評価データセット（単一真実源: SSOT）
    {skill_name}_edd.evalset.json
    test_config.json   # Google ADK 2.0 公式 EvalConfig（IN_ORDER & Rubrics 設定）
```

