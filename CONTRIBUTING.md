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
│   ├── SETUP.md            # 人間向けの環境構築・LLM認証・MCP起動ガイド
│   └── src/edd_agent_tools/
│       ├── AGENTS.md       # AIエージェント向けシステム制約（ドキュメント規約の真実のソース）
│       └── docs/           # パッケージドキュメントセンター（Whyの集約先）
│           ├── progressive_disclosure.md # 3層リソース分離（scripts, references, assets）規約
│           ├── prompt_syntax.md          # Imperative文体・客観的プロンプト規約
│           ├── skill_patterns.md         # 4大スキル構造パターン
│           ├── design_philosophy.md      # スキル設計思想・フォルダ構成規約
│           ├── test_architecture.md      # テスト Generator-Executor ペアリング仕様
│           ├── eval_design.md            # サンドボックス隔離・アサーションポリシー
│           └── sandbox_design.md         # Gymnasium仮想環境（DI）とCLI仕様
└── src/                    # 自己進化エージェントの本体およびスキル（Tier管理下）
    └── skills/             # すべてのスキルおよび合成ワークフロー（3層リソース構造）
        ├── skill-creator/  # 4段階品質保証パイプラインによるスキル自律生成エンジン
        ├── skill-optimizer/# テスト・診断・差分修復・連鎖回帰テストの自律改善ループ
        ├── skill-diagnoser/# テスト失敗根本原因分析・3層差分改善計画エンジン
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

1. **単一真実源 (Markdown-First)**:
   - スキルの振る舞い、インターフェース、意思決定ツリー、手順はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化します。
2. **3層リソース分離 (Progressive Disclosure)**:
   - `scripts/`: 直接実行可能な決定論的スクリプト（Python/Bash）
   - `references/`: ドメイン知識・API仕様・スキーマ（オンデマンド参照資料）
   - `assets/`: 出力用テンプレート・素材・ボイラープレート
3. **ボイラープレートの排除 (Minimal Boilerplate)**:
   - `nodes/`, `handlers/`, `workflow.py`, `models.py` などの過剰な多層ラッパーを作らず、フラットで簡潔な実装を行ってください。
4. **客観的指示文体 (Imperative Form)**:
   - 全体指示文は動詞起点（"To accomplish X, do Y" / "Xを実行するには、Yを行う" 形式）で記述し、会話調を排除してください。
   - Frontmatter の `description` は第三者視点（"This skill should be used when..."）で100 words以内で簡潔に記述してください。
