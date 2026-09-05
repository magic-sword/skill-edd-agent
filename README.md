# Self-Evolving EDD Agent
**〜Anthropic公式標準の Markdown-First & Progressive Disclosure を備えた、Google ADKスキルの自己進化型 評価駆動開発（EDD）エージェント〜**

本プロジェクトは、Google の **Agent Development Kit (ADK) 2.0** および Anthropic の **Progressive Disclosure（段階的情報開示）** 設計思想を融合し、AIエージェントが自律的に新しいスキル（機能）を設計、開発、テスト、評価し、適切な Tier 状態管理を経て自身へマウント（統合）する **「自己進化型 評価駆動開発 (Self-Evolving EDD: Evaluation-Driven Development) エージェント」** です。

Google 『Agent Skills』ホワイトペーパー（May 2026）に完全準拠した **「次世代多層テスト評価ハーネス（ADK 2.0 純正評価統合・3大 Trajectory モード・pass^k 連続信頼性指標・Co-loaded 共存テスト・Human Sign-off ゲート）」** を搭載しています。

Kaggle Competition: [Vibe Coding Agents Capstone Project (Freestyle Track)](https://www.kaggle.com/competitions/vibecoding-agents-capstone-project) 提出プロジェクト。

---

## 1. 背景と中核コンセプト (Background & Core Concept)

### 💡 ADKの思想への共感と課題意識
Googleの **ADK 2.0** が提唱する「スキル」によるエージェント構築は、エージェント開発の理想形です。段階的にスキルを適用することで、エージェントは強化学習のオプション（スキル）獲得と非常に近い形で、人間がメンテナンス可能かつ他エージェントに継承可能な「スキル」という形で知識を蓄積できます。

しかし、従来のスキル開発では以下のような課題がありました：
*   **多層ボイラープレートの肥大化**: 多層ラッパーが乱立し、トークン消費と保守負荷が増大（Context Debt）。
*   **EDD（評価駆動開発）の難しさ**: AIの生成物を的確に検証し、ハルシネーションや誤ったツール呼び出し（偽陽性）を防ぐハーネス（制約）を設計するのは人間にとっても極めて困難。

> [!IMPORTANT]
> **本プロジェクトの結論**
> エージェント開発者が何よりもまず優先して構築すべきなのは、**「評価駆動開発を自律的に行うメタエージェント（Two-Tier アーキテクチャ）」**です。
> 人間の自然言語指示（Vibe）を受け取り、エージェント自身が安全に **Markdown-First** かつ **Progressive Disclosure（段階的情報開示）** でスキルを生成・テスト・評価し、厳格な品質防壁をクリアしたスキルだけを自律的に自身の武器（ツール）としてマウント（統合）します。

---

## 2. 責務分離とコアアーキテクチャ (Two-Tier Architecture)

本システムは、**「不変のプラットフォーム基盤（pip: `edd-agent-tools`）」** と **「エージェントが自律的に所有・進化させるスキル資産（`src/skills/`）」** を厳密に分離しています。

```mermaid
flowchart TD
    subgraph PlatformLayer ["不変プラットフォーム層 (pip: edd-agent-tools)"]
        Validator["SkillValidator (AST/構文静的リンター, examples/対応)"]
        AdkEval["AdkEvalAdapter (Google ADK 2.0 純正 LLM Judge & Position Swapping)"]
        SimRunner["SimulationEvalRunner (3大 Trajectory: EXACT / IN_ORDER / ANY_ORDER)"]
        ContractRunner["ContractTestRunner (pass^k 連続一貫性検証 & サンドボックス)"]
        CoLoadRunner["CoLoadedEvalRunner (複数スキル同時展開時の Context Rot ベンチマーク)"]
        StateEngine["SkillsState & DAG Validator (状態・Tier 1~3 管理)"]
        Optimizer["SkillOptimizer (Human Sign-off ゲート & 一括最適化)"]
        Packager["SkillPackager (安全な ZIP アーカイブ生成)"]
        ADKAdapter["ADK 2.0 Native Adapter (SkillToolset, EddSkillRegistry)"]
        UnifiedCLI["統合 CLI edd (CLI-as-an-API 動的ディスパッチ)"]
    end

    subgraph SkillAssets ["自己改善スキル資産層 (src/skills/)"]
        Creator["skill-creator: スキル設計・Markdownテンプレート・雛形生成"]
        Evolver["skill-evolver: 失敗診断・自己修復ループ・Tier昇格"]
        DomainSkills["case-converter, secret-sanitizer 等の実用ドメインスキル"]
    end

    PlatformLayer -->|基盤SDK・テストハーネス提供| SkillAssets
    SkillAssets -->|自己改善ループ (Markdown/Scripts/Assets/Examples/Tests修正)| SkillAssets
```

1.  **単一真実源の原則 (Markdown-First & Template Assets)**
    *   スキルの仕様定義はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化。パッケージ内部に公式標準の雛形テンプレートを同梱。
2.  **Progressive Disclosure (段階的リソース分離) & ルーティング設計**
    *   **Level 1: YAML Frontmatter (Routing Algorithm)**:
        - `description` は動詞起点（Verb-led sentence）で開始し、「Use when...（発動条件）」および「Do NOT use for...（除外条件）」を明記（50〜100 words）。
    *   **Level 2: SKILL.md 本文 (Instructions)**:
        - 客観的動詞起点（Imperative form: "To accomplish X, do Y"）で記述。Context Rot 対策として 5,000 words 以内に抑え、詳細仕様は `references/` に分離。
    *   **Level 3: Bundled Resources (On-demand & Execution)**:
        - `scripts/`: 直接実行可能な決定論的スクリプト（Zero-dependency, CLI `--help` 対応, Black-box 実行）。**Shift Intelligence Left** により決定論的処理をコードへオフロード。
        - `references/`: LLMがオンデマンドで読む詳細ドキュメント・スキーマ
        - `assets/`: 成果物にコピー・流用するためのテンプレート・素材
        - `examples/`: エージェントが真似できる具象コード例・パターン集
        - `tests/`: Google ADK 2.0 公式 EvalSet 評価データセット（`<skill-name>.test.json`: 単一真実源: SSOT、ADK ディレクトリ自動探索適合）
3.  **Google ADK 2.0 純正ランタイム完全一致命名規約**
    *   ADK 2.0 公式ランタイム制約（`skill_dir.name == frontmatter.name`）に基づき、ディレクトリ名・スキル名は **`kebab-case`（例: `case-converter`）** で完全一致。内部スクリプトは Python 標準の **`snake_case`（例: `case_converter.py`）** を厳格適用。
4.  **Google ADK 2.0 純正評価統合 & 車輪の再発明の完全排除**
    *   ADK 2.0 の `TrajectoryEvaluator`（3大モード: EXACT / IN_ORDER / ANY_ORDER）および `ResponseEvaluator`（ROUGE-1 `response_match_score`）、そして公式の **`RubricBasedFinalResponseQualityV1Evaluator`** を直接駆動。アドホックな正規表現判定や独自手動キーワード照合（偽ルーブリック判定）、手書き軌跡比較ループを全廃し、エージェント実行・テストケースのツール呼び出しは ADK 2.0 純正の **`run_skill_script`**（args: `skill_name`, `file_path`, `args`, `positional_args`）を第1級の標準（Primary Standard）として採用。
    *   プライベート属性（`_tools`）の裏口アクセスやスクリプト実行の一時展開ロジック自前再実装（旧コピペコード）、自前 `subprocess.run` 実行コードを完全排除。ドメインエンティティおよび契約テスト（`ContractTestRunner`）から ADK 2.0 純正の公式 `RunSkillScriptTool`、`_SkillScriptCodeExecutor`、および `UnsafeLocalCodeExecutor` に委譲し、トップレベルエージェントにも公式推奨通り `code_executor` を直接注入。
    *   エージェントプロンプトからのスキル名ハードコードや `SkillToolset` 自動注入指示との重複を全廃し、ADK 2.0 純正の Progressive Disclosure（`list_skills` 探索および Toolset 自動プロンプト注入）と ADK 推奨 Callbacks（`before_agent_callback` / `after_agent_callback`）を活用するアーキテクチャへと刷新。
    *   `SimulationEvalRunner` において `AgentEvaluator` の例外ログを構造解析し、従来のバイナリ全勝/全敗丸めを解消。各テストケース単位での合否判定および詳細コンテキスト（`FailedCaseDetail`）を抽出・記録。
    *   Frontmatter の `allowed-tools` は ADK 2.0 純正仕様であるスペース区切り文字列として正規化し、`metadata.adk_additional_tools` による追加ツール公開に対応。
5.  **白書（May 2026）4大 Eval Coverage Checklist (`--coverage`)**
    *   白書 Section 4 の 4大必須評価条件（Trigger >= 90%, Execution/Trajectory 100%, Regression 0 drops, Token Budget/Co-loaded 5~15 skills）を一括判定・チェックリスト出力。
6.  **$pass^k$ (Sustained Reliability) & 3大 Tool Trajectory 評価モード**
    *   複数回連続実行での全勝を要求する $pass^k$ 評価と、`EXACT`（完全一致）、`IN_ORDER`（順序付き部分列）、`ANY_ORDER`（順序不問）による厳密なツール呼び出し軌跡検証。
7.  **Human Sign-off ゲート (Tier 3: Action-Allowed)**
    *   不可逆操作が許可される Tier 3 昇格時には、人間の明示的承認を必須化。
8.  **白書標準 EDD (Evaluation-Driven Development) インバージョン開発と単一真実源 (SSOT)**
    *   `SKILL.md` を執筆する前に、まず `tests/<skill-name>.test.json`（単一真実源: SSOT）として **3つの正例 ＋ 3つの負例（計6ケース、白書 Page 22 必須要件）** の Google ADK 2.0 公式 `EvalSet`（`eval_set_id`, `eval_cases`, `conversation`, `Invocation`, `intermediate_data.tool_uses`, `rubrics`）を確定し、ツールの呼び出し軌跡と採点ルーブリックを先行定義。
    *   **責務分離の原則 (Responsibility Separation)**: ツール呼び出し・引数・順序の検証は `intermediate_data.tool_uses`（Trajectory レイヤー）に集約し、`rubric` はエージェントの最終出力品質（正確性・簡潔性・会話フィラーの排除・負例時の適切な振る舞い）に特化。
9.  **白書 Appendix A minimal SKILL.md 6大必須セクション標準**
    *   すべてのスキルは、白書 Appendix A が定める 6 つの必須セクション（`When to use`, `When NOT to use`, `Workflow`, `Examples`, `Output format`, `Anti-patterns to avoid`）を標準実装。
10. **Google ADK 2.0 純正 LocalCodeExecutor / RunSkillScriptTool 統合 & AgentEvaluator 直結**
    *   ADK 公式の `google.adk.code_executors.UnsafeLocalCodeExecutor` を標準注入した `RunSkillScriptTool` にスクリプト実行を直接委譲し、モンキーパッチや自前展開コードに頼らず正規の手順で安全にコードを実行。
    *   `edd adk-eval <skill-name>` により、Google ADK 2.0 公式 `AgentEvaluator.evaluate()` を直接ワンストップ実行可能。
11. **Don't Reinvent MCP as Scripts (MCP再発明の禁止)**
    *   外部APIやネットワーク通信は MCP ツールに委譲し、スキルスクリプト内で巨大な HTTP クライアントを再発明しない。スキルは Know-how（決定論的手順と処理）に集中。


---

## 3. 実装スキル一覧 (Skills & Workflows)

### 🛠 メタスキル & ドメインスキル
| スキル名 | 役割 / 機能 | Tier | 特徴 |
| :--- | :--- | :---: | :--- |
| **`skill-creator`** | スキル設計・雛形生成・配布パッケージャ | Tier 1 | Anthropic & Google ADK 準拠の対話的スキル作成ガイド、雛形生成、AST静的検証、配布用 ZIP パッケージャ、契約テスト完備。 |
| **`skill-evolver`** | 統合評価・失敗診断・自己修復・Tier昇格 | Tier 1 | 契約テスト・シミュレーション評価の実行、失敗コンテキスト診断、自律的自己修復ループ、依存連鎖回帰テスト（Cascade Testing）、および Tier 1〜3 昇格判定を統合オーケストレーション。 |
| **`case-converter`** | テキストケース変換 | Tier 2 | camelCase, snake_case, PascalCase, kebab-case, CONSTANT_CASE, Title Case 等の相互変換を行う Zero-dependency 実用スキル。 |
| **`secret-sanitizer`** | 機密情報マスキング・サニタイズ | **Tier 3** | APIキー、Bearerトークン、パスワード、JWT、IPアドレス、メールアドレスを検出・マスクする Zero-dependency ツール。全品質防壁を突破。 |

---

## 4. クイックスタート (Quick Start)

### パッケージのインストール
```bash
pip install -e edd-agent-tools
```

### 統合 CLI (`edd`) によるスキル操作
```bash
# 1. スキルの直接実行 (動的ディスパッチ)
edd run secret-sanitizer --input "My key is sk-1234567890abcdef"
# またはスキル名を直接サブコマンドとして指定可能 (Git プラグイン方式)
edd secret-sanitizer --input "My key is sk-1234567890abcdef"

# 2. 新規スキル雛形の初期化
edd init my-new-skill --pattern task_based

# 3. 高度な静的バリデーション (Linter / AST 解析)
edd validate src/skills/my-new-skill

# 4. 配布用 ZIP パッケージング
edd package src/skills/my-new-skill --out dist

# 5. 白書 4大 Eval Coverage Checklist 検証
edd eval my-new-skill --coverage

# 6. EDD 多層評価 (Trajectory / pass^k / Co-loaded 対応)
edd eval my-new-skill --type trajectory --trajectory-mode in_order
edd eval my-new-skill --pass-k 3
edd eval my-new-skill --co-loaded

# 7. Google ADK 2.0 公式 AgentEvaluator / adk eval 評価
edd adk-eval my-new-skill
edd adk-eval my-new-skill --cli

# 8. Tier 昇格 & 失敗診断 & 一括最適化 (Human Sign-off 対応)
edd tier-gate my-new-skill --tier 3 --yes
edd diagnose my-new-skill
edd optimize my-new-skill --tier 3 --yes
```

### Google ADK 2.0 エージェント / A2A サーバーの起動
```bash
# A2A 互換サーバーの起動 (ポート 8001)
python src/main.py
```

### テストスイートの実行
```bash
pytest
```
