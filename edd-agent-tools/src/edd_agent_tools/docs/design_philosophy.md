# Agent Skill 設計思想 (Design Philosophy)

本プロジェクトにおける Google ADK 2.0 および Anthropic 標準（Markdown-First & Progressive Disclosure）スキルの設計思想とベストプラクティスを記録します。

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
    - 軽量ユーティリティ（例: `case-converter`）は Python 標準ライブラリのみで完結させます。
    - 外部ライブラリ依存（例: `docx`, `xlsx`, `playwright` 等）が必要なスキルは、Anthropic 公式標準に従い `SKILL.md` の `## Requirements & Prerequisites` に必要な pip パッケージを明記します（環境構築されている前提で実行）。`SkillValidator` が AST 解析により記述漏れを自動検知します。

---

## 1. コア思想とアーキテクチャ原則

### ① Two-Tier Architecture（不変プラットフォーム vs 自己改善資産）
* **不変プラットフォーム層 (`edd-agent-tools`)**:
  - スキルのスキーマ検証（`SkillValidator`）、サンドボックス実行（`LocalWorkspaceEnv`）、多層評価（`ContractTestRunner`）、Tier状態管理（`SkillsState`）、ZIPパッケージャなどの決定論的インフラを提供。
  - プロンプト文体や生成ロジックをコード内に過度にハードコードしない。
* **自己改善スキル資産層 (`src/skills/`)**:
  - スキル作成用の Markdown テンプレート素材（`assets/templates/`）、プロンプト定義（`SKILL.md`）、決定論的スクリプト（`scripts/`）、契約テスト（`tests/`）を集約。
  - エージェントが自己改善（プロンプト進化）する際、pip パッケージのコードを変更することなく安全に進化可能。

### ② 単一真実源とカスケード解決 (Cascading Template Resolver)
* 仕様書兼プロンプトである **`SKILL.md` を唯一の真実源** とし、自然言語（Markdown）とコード（Python）のシームレスな統合を図ります。
* テンプレート解決は **カスケード解決機構（Cascading Template Resolver）** を採用：
  1. ワークスペース側の自己改善テンプレート（`skills/skill-creator/assets/templates/`）を最優先で探索
  2. 存在しない場合はパッケージ組み込みテンプレート（`edd_agent_tools.packaging.templates`）へ安全にフォールバック
  これにより、エージェントがプロンプトテンプレートを自己改善すると、以降の `edd init` で生成されるスキルの初期品質が自律的に向上します。

### ③ Progressive Disclosure（3層リソース分離）
* コンテキストウィンドウの効率化と信頼性の両立を図るため、スキル資産を3層に分離します：
  1. **Level 1: YAML Frontmatter**（常時ロード: `name`, `description`）
  2. **Level 2: SKILL.md 本文**（トリガー時ロード: 意思決定ツリー、手順、ガイドライン）
  3. **Level 3: 3層リソース**（オンデマンド実行・ロード）
     - `scripts/`: 決定論的Python/Bashスクリプト（Zero-dependency, CLI対応）※ドメイン独自処理がある場合のみ配置
     - `references/`: ドメイン知識・API仕様・スキーマ
     - `assets/`: 出力用テンプレート・素材
     - `tests/`: 契約テストおよびシミュレーション評価データ（`*.evalset.json`）

### ④ Google ADK 2.0 ネイティブ統合 (`SkillToolset`, `SkillRegistry`, `create_adk_skill_toolset`)
* 全スキルの Python 関数を直接 `FunctionTool` として一括展開するアンチパターン（Context Bloat）を排除し、Google ADK 2.0 標準の `SkillToolset` による Progressive Disclosure ライフサイクル（`list_skills` ➔ `load_skill` ➔ `load_skill_resource` ➔ `run_skill_script`）を採用。
* `EddSkillRegistry` により、ADK 純正の `SkillRegistry` 抽象クラスに `SkillsState`（Tier 状態・DAG 解析）を適合させ、動的検索（`SearchSkillsTool`）およびオンデマンドフェッチを提供。
* `create_adk_skill_toolset` ファクトリにより、Tier 状態（Production / Verified / Draft）に応じたフィルタリングと、ADK 2.0 の自動システム命令注入（`DEFAULT_SKILL_SYSTEM_INSTRUCTION`）を活用した安全なエージェント統合を提供。

### ⑤ スキルの完全ポータビリティと自己完結型テスト (Self-Contained Evaluation)
* 各スキルは単体で外部プラットフォーム（Claude Code, Antigravity, Cursor, ADK 等）へドロップイン可能な自己完結性を持つ。
* 各スキルの `tests/` ディレクトリに契約テスト（`*.evalset.json`）を同梱し、単体で `edd eval` による 100% 契約検証を実施可能。

### ⑥ 4次元ネガティブ・ハーネス (`When NOT to Use` による過剰適用防止)
* 以下の4軸から客観的な除外条件（When NOT to use）を導出し、過剰適用（Over-tooling）や競合による誤発火を防止：
  1. **粒度境界 (Granularity)**: 単発のワンライナーや標準OSコマンドで完結する軽微なタスク。
  2. **技術的限界 (Out-of-Scope)**: ドメイン範囲外の高度な変換や別領域の処理。
  3. **ライフサイクル分離 (Lifecycle)**: 前後のフェーズ（作成、診断、評価、最適化）の住み分け。
  4. **インベントリ照合 (Inventory)**: 既存スキルで既にカバーされているタスク。

### ⑦ 4段階品質保証パイプライン (4-Stage Quality Gate)
* スキルの自律生成からマウントまでの品質を保証する4段階の防壁：
  - **Stage 1 (Authoring & Scaffolding)**: `assets/templates/` を活用した論理設計と雛形生成（`edd init`）
  - **Stage 2 (Static Validation)**: `SkillValidator` による静的リンター（構文・実在整合性・Imperative文体・Prerequisites外部依存照合・DAG依存関係）
  - **Stage 3 (Contract & Multi-Layer Evaluation)**: サンドボックス環境（`LocalWorkspaceEnv`）での契約テスト（I/O型検査）およびシミュレーション評価（Trigger / Trajectory / Golden）
  - **Stage 4 (Self-Healing Loop & Cascade Gating)**: 失敗診断（`edd diagnose`）➔ 修正 ➔ 連鎖回帰テスト（`CascadeTestRunner`）➔ Tier 昇格

### ⑧ 動的ディスパッチ (Dynamic Dispatch) ＆ 統合 CLI (`edd`)
* スキルが自律的に増殖・追加されてもパッケージ本体の再インストールやコード修正を一切不要とするため、ファイルシステムベースの動的ディスカバリ（`edd run <skill-name>` / `edd <skill-name>`）を採用。

---

## 2. システム・アーキテクチャのレイヤード構造

```
edd_agent_tools/
├── core/           # 共通ドメインエンティティ (Skill, SkillTests)
├── state.py        # 状態管理・探索・DAG解析 (SkillsState)
├── models/         # データモデル (SkillSpec, SkillTier, EvalCaseSet, EvalRunResult)
├── validation/     # 汎用静的リンター (SkillValidator, ValidationResult, AST解析, Prerequisites照合)
├── packaging/      # ZIP パッケージャ (SkillPackager), スキャフォールド (SkillScaffolder, Cascading Resolver)
├── evaluation/     # 契約テスト (ContractTestRunner), シミュレーション, 診断 (SkillDiagnoser), 最適化 (SkillOptimizer), サンドボックス (LocalWorkspaceEnv)
├── adk/            # Google ADK 2.0 連携 (create_adk_skill_toolset, EddSkillToolset)
├── mcp/            # FastMCP サーバー (edd-agent-mcp)
└── cli.py          # 統合 CLI (edd run/init/validate/package/eval/tier-gate/diagnose/optimize/list)
```

---

## 3. スキルフォルダ構造の規約 (Standard Layout)

```
src/skills/{skill-name}/
  SKILL.md       # YAML Frontmatter ('This skill should be used when...') + Markdown仕様書 (SSOT)
  scripts/       # 決定論的スクリプト（直接実行可能・CLI対応・Zero-dependency、ドメイン処理がある場合のみ）
    {skill_name}.py
  references/    # ドメイン知識・仕様・スキーマ（オンデマンド参照）
    guide.md
  assets/        # 出力用テンプレート・素材（任意・空ディレクトリ不可）
    templates/   # スキル作成用のMarkdownテンプレート素材（skill-creatorの場合）
  tests/         # 評価データセット（{skill_name}_contract.evalset.json 等）
```
