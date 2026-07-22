# Self-Evolving EDD Agent 貢献ガイドライン (Contributing Guide)

本リポジトリ全体（ADK自己進化エージェントおよび EDD 開発コアツール）に貢献（コード修正、スキル追加、ドキュメント整備など）してくださる共同開発者（人間・AI）の皆様へ、プロジェクト全体の設計思想とドキュメント規約を定義します。

---

## 1. ディレクトリ構成と役割分担

本プロジェクトは、以下の役割分担でディレクトリとドキュメントが構成されています。

```
/workspace/ (リポジトリルート)
├── README.md               # プロジェクト全体の「玄関口」（Why / 実証結果）
├── CONTRIBUTING.md         # 【本書】共同開発者（人間）向けの全体開発規約
├── edd-agent-tools/        # EDD開発を支援する共有ヘルパーライブラリ（Pythonパッケージ）
│   ├── README.md           # パッケージの「スリム化インデックス玄関口」（docs/へのリンク）
│   ├── SETUP.md            # 人間向けの環境構築・LLM認証・MCP起動ガイド
│   ├── CONTRIBUTING.md     # パッケージ開発の貢献リンクガイド（AGENTS.mdへ誘導）
│   └── src/edd_agent_tools/
│       ├── AGENTS.md       # AIエージェント向けシステム制約（ドキュメント規約の真実のソース）
│       └── docs/           # パッケージドキュメントセンター（Whyの集約先）
│           ├── design_philosophy.md # スキル設計思想・フォルダ構成規約
│           ├── test_architecture.md # テスト Generator-Executor ペアリング仕様
│           ├── eval_design.md       # サンドボックス隔離・アサーションポリシー
│           └── sandbox_design.md    # Gymnasium仮想環境（DI）とCLI仕様
└── src/                    # 自己進化エージェントの本体およびスキル（Tier管理下）
    ├── workflows/          # 自己進化ワークフローエージェント（skill-developer等）
    └── skills/             # 自動生成・マウントされる個別スキル群
        └── workflow-designer/
            └── references/ # ワークフロー設計および経路評価の専門仕様書
                └── workflow_trajectory_eval_design.md
```

---

## 2. ドキュメント化の設計思想 (Single Source of Truth)

本プロジェクトでは、情報の陳腐化、不整合、ハルシネーションを防ぐために、ドキュメント配置の **「関心の完全分離」** を徹底しています。

*   **API個別仕様 (What / How to Call) ➔ ソースコード内 (Pydoc)**:
    *   クラスや関数の引数、型、戻り値、例外などの仕様は、コード内の Google スタイル Docstring (Pydoc) および型ヒントのみに記述し、Markdownには絶対に重複記述しないでください。
*   **横断的システム制約 (How / System Rules) ➔ パッケージ内 [AGENTS.md](edd-agent-tools/src/edd_agent_tools/AGENTS.md)**:
    *   AIエージェントがコード生成時に遵守すべき厳密な制約は、パッケージ内蔵の `AGENTS.md` に一元管理（シングルソース）されています。
*   **設計の背景・意図 (Why / Architecture) ➔ パッケージ内 `docs/`**:
    *   なぜその設計になっているのかという背景やダイアグラムは、パッケージ内の `docs/` 配下の Markdown 設計書にのみ集中配置します。

詳細な規約ルール（Googleスタイル Docstring の記述規約など）については、システム規約の唯一の真実のソースである **[edd_agent_tools/AGENTS.md](edd-agent-tools/src/edd_agent_tools/AGENTS.md)** を必ず確認し、遵守してください。
