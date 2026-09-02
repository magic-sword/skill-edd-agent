# Self-Evolving EDD Agent 貢献ガイドライン (Contributing Guide)

本リポジトリ全体（ADK自己進化エージェントおよび EDD 開発コアツール）に貢献（コード修正、スキル追加、ドキュメント整備など）してくださる共同開発者（人間・AI）の皆様へ、プロジェクト全体の設計思想とドキュメント規約を定義します。

---

## 1. ディレクトリ構成と役割分担

本プロジェクトは、以下の役割分担でディレクトリとドキュメントが構成されています。

```
/workspace/ (リポジトリルート)
├── README.md               # プロジェクト全体の「玄関口」（Why / アーキテクチャ / クイックスタート）
├── CONTRIBUTING.md         # 【本書】共同開発者（人間）向けの全体開発規約
├── demo_self_evolution.py  # 自己進化エージェントの End-to-End 実演デモスクリプト
├── skills_state.json       # プロジェクト全体のスキルの Tier 状態管理ファイル
├── edd-agent-tools/        # EDD開発を支援する共有ヘルパーライブラリ（Pythonパッケージ）
│   ├── README.md           # パッケージの「スリム化インデックス玄関口」（docs/へのリンク）
│   ├── SETUP.md            # 人間向けの環境構築・インストール・MCP起動ガイド
│   └── src/edd_agent_tools/
│       ├── AGENTS.md       # AIエージェント向けシステム制約（ドキュメント規約の真実のソース）
│       └── docs/           # パッケージドキュメントセンター（Whyの集約先）
│           ├── progressive_disclosure.md # リソース分離（scripts, references, assets, examples, tests）規約
│           ├── prompt_syntax.md          # Imperative文体・客観的プロンプト規約
│           ├── skill_patterns.md         # スキル構造パターン設計ガイド
│           ├── design_philosophy.md      # スキル設計思想・Two-Tier 構造
│           ├── test_architecture.md      # 多層テスト・ADK 評価統合仕様
│           ├── eval_design.md            # サンドボックス隔離・アサーションポリシー
│           └── sandbox_design.md         # 仮想環境（DI）とCLI仕様
└── src/                    # 自己進化エージェントの本体およびスキル（Tier管理下）
    └── skills/             # すべてのスキル（Progressive Disclosure構造）
        ├── skill-creator/  # スキル設計・雛形生成・パッケージャ
        ├── skill-evolver/  # 評価・失敗診断・自己修復・Tier昇格を司る自己改善メタスキル
        ├── case-converter/ # テキストケース変換
        ├── secret-sanitizer/ # 機密情報マスキング・サニタイズ (Tier 3)
        └── ...
```

---

## 2. ドキュメント化の設計思想 (Single Source of Truth)

本プロジェクトでは、情報の陳腐化、不整合、ハルシネーションを防ぐために、ドキュメント配置の **「関心の完全分離」** を徹底しています。

*   **API個別仕様 (What / How to Call) ➔ ソースコード内 (Docstring)**:
    *   クラスや関数の引数、型、戻り値、例外などの仕様は、コード内の Google スタイル Docstring および型ヒントのみに記述し、Markdownには絶対に重複記述しないでください。
*   **横断的システム制約 (How / System Rules) ➔ パッケージ内 [AGENTS.md](edd-agent-tools/src/edd_agent_tools/AGENTS.md)**:
    *   AIエージェントがコード生成時に遵守すべき厳密な制約は、パッケージ内蔵の `AGENTS.md` に一元管理（シングルソース）されています。
*   **設計の背景・意図 (Why / Architecture) ➔ パッケージ内 `docs/`**:
    *   なぜその設計になっているのかという背景やダイアグラムは、パッケージ内の `docs/` 配下の Markdown 設計書にのみ集中配置します。

---

## 3. スキル開発規約 (Anthropic 標準 & Progressive Disclosure)

新規スキルを追加または既存スキルを改修する際は、以下の規約を遵守してください：

1. **単一真実源 (Markdown-First & CLI-as-an-API)**:
   - スキルの振る舞い、インターフェース、意思決定ツリー、手順はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化します。
   - メタスキル（`skill-creator`, `skill-evolver`）は `pip install edd-agent-tools` を前提とし、統合 CLI `edd` を直接呼び出す手順書（CLI-as-an-API）として記述します。
2. **Progressive Disclosure (リソース分離)**:
   - `scripts/`: 直接実行可能な決定論的スクリプト（Python/Bash, `--help` 必須, Black-box 実行）
   - `references/`: ドメイン知識・API仕様・スキーマ（オンデマンド参照資料）
   - `assets/`: 出力用テンプレート・素材・ボイラープレート（空ディレクトリは残置しない）
   - `examples/`: エージェントが真似できる具象コード例・パターン集
   - `tests/`: 白書 Snippet 3 形式評価データセット（`<skill-name>_edd.evalset.json`: 単一真実源: SSOT）
3. **命名規約 (ADK 2.0 ランタイム完全一致)**:
   - ディレクトリ名・スキル名は `kebab-case`（例: `case-converter`）で完全一致させます（ADK 2.0 `load_skill_from_dir` の必須要件）。
   - スクリプト名は Python 標準の `snake_case`（例: `case_converter.py`）とします。
4. **依存関係ポリシー (Prerequisites & Zero-Dependency)**:
   - 軽量ユーティリティは Python 標準ライブラリのみで完結させます。
   - 外部ライブラリを必要とするスキルは、`SKILL.md` の `## Requirements & Prerequisites` に必要な pip パッケージを明記します（`SkillValidator` が AST 解析により自動検証）。
   - スキル内部から `import edd_agent_tools` などの直接 Python import は行わず、CLI/IO 規約でのみ連携します。
5. **Don't Reinvent MCP as Scripts (MCP再発明の禁止)**:
   - 外部APIやネットワーク通信は MCP ツールに委譲し、スキルスクリプト内で巨大な HTTP クライアントを再発明してはなりません。スキルは Know-how（決定論的手順と処理）に集中します（`SkillValidator` が AST 解析で検知・警告）。
6. **白書標準 EDD インバージョン開発と単一真実源 (SSOT)**:
   - `SKILL.md` の本文を執筆する前に、まず `tests/<skill-name>_edd.evalset.json` に白書 Snippet 3 標準フォーマットの 3〜4 つの評価ケース（`case_id`, `input`, `expected_skill`, `expected_tool_calls`, `expected_output_format`, `rubric`、正例＋負例完備）を先行定義してください。
   - 乱立する複数のテストファイルを排し、契約テスト・トリガー判定・Trajectory・ルーブリック評価をこの単一アセットから決定論的に実行します。

6. **4次元ネガティブ・ハーネス (`When NOT to Use This Skill`)**:
   - 粒度境界、技術的限界、ライフサイクル分離、インベントリ照合の4軸から客観的な除外条件を明記し、過剰適用を防ぎます。
7. **客観的指示文体 (Imperative Form & Routing Algorithm)**:
   - 全体指示文は動詞起点（"To accomplish X, do Y" / "Xを実行するには、Yを行う" 形式）で記述し、会話調を排除してください。
   - Frontmatter の `description` はエージェントのルーティングアルゴリズムです。動詞起点（Verb-led sentence）で開始し、「Use when...（発動条件）」および「Do NOT use for...（除外条件）」を明記してください（50〜100 words, ≤1024 chars）。
   - Context Rot 対策として、`SKILL.md` 本文は 5,000 words 以内に抑え、詳細仕様は `references/` に分離してください。
   - Context Debt 対策として、`ALWAYS` や `NEVER` などの大文字命令を詰め込まず「理由を付記（Give the reason, not just the rule）」してください。

---

## 4. 品質防壁と Tier 昇格基準 (The Read / Draft / Act Ladder)

ホワイトペーパー（May 2026）に準拠し、スキルは以下の 3 段階の防壁を経て昇格・マウントされます：

| Tier | 権限レベル | 必須合格条件 |
| :---: | :--- | :--- |
| **Tier 1** | **`READ_ONLY`** (Production Gate) | 静的バリデーション（`edd validate` 警告/エラー0件）+ CLI 契約テスト（100% 合格）+ トリガー精度（90% 以上） |
| **Tier 2** | **`DRAFT_ONLY`** (Verified Gate) | ゴールデンデータセット評価（90% 以上）+ 上位依存スキルの連鎖回帰テスト（Cascade Regression 100% パス） |
| **Tier 3** | **`ACTION_ALLOWED`** (Mastered Gate) | Tool Trajectory 評価（`IN_ORDER` または `EXACT`）+ $pass^k$ 持続的一貫性（$k \ge 3$ 連続合格）+ Co-loaded 共存テスト + **人間の明示的承認（Human Sign-off: `--yes`）** |
