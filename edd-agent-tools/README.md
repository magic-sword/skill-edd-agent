# edd-agent-tools

EDD（評価駆動開発）による自律型 AI エージェントおよびスキルの開発・運用をサポートするための共通ツールおよびヘルパーライブラリ。

> [!NOTE]
> 具体的な利用例や API 仕様は、本パッケージの各主要クラス（`Skill`, `SkillsState`, `TestGenerator`, `TestExecutor` 等）の Docstring 内にサンプルコード（`Examples:`）として実装と一体で記述されています。

---

## 1. 主な機能と特徴

*   **型安全な Pydoc / Google スタイル Docstring (What)**
    すべてのパブリック API に型ヒントと Google スタイルの Docstring を完結して定義。AIエージェントによるインプロセスな動的型解決（`inspect`）の成功率を最大化します。
*   **Gymnasium 互換サンドボックス隔離環境 (`WorkspaceEnvProtocol`)**
    自動生成されたコードやテスト実行による環境破壊を防ぐため、OS直接操作を禁止した隔離サンドボックス環境（`LocalWorkspaceEnv`）を提供。Gitロールバックと確実な差分マージに対応しています。
*   **動的ディスパッチテストフレームワーク (`TestGenerator` / `TestExecutor`)**
    テストケースの「生成」と「実行」をプロトコルに基づいて完全に分離し、100%決定論的で再現可能なペアリングテストを実現します。
*   **Gemini API クライアント & システムルール自動検出**
    `GeminiRequest` の実行時に、プロジェクトルール（`AGENTS.md`）やパッケージに同梱されたシステム制約を自動検出し、プロンプトにインプリシットにマージして送信します。
*   **ローカル MCP サーバー統合 (`edd-agent-mcp`)**
    AIエージェントや AI IDE に対し、本プロジェクトの「設計思想」「システム制約」を URI (`edd://`) 経由でオンデマンド遅延ロードさせるための Model Context Protocol サーバーを同梱。

---

## 2. 詳細設計書インデックス (Detailed Documents)

二重管理と情報の陳腐化を防ぐため、システム全体の「Why（背景・設計思想）」は以下のドキュメントセンターに一元集約されています。

*   **[design_philosophy.md](src/edd_agent_tools/docs/design_philosophy.md)**: スキル設計思想・ADK 2.0 スキル定義規約・フォルダ構成規約。
*   **[test_architecture.md](src/edd_agent_tools/docs/test_architecture.md)**: テストの Generator-Executor ペアリングパターンの目的、標準 Protocol 仕様。
*   **[eval_design.md](src/edd_agent_tools/docs/eval_design.md)**: サンドボックス隔離設計とテストの合否アサーション判定論理。
*   **[sandbox_design.md](src/edd_agent_tools/docs/sandbox_design.md)**: Gymnasium 互換の隔離環境（DI）と CLI ランナーの詳細。

---

## 3. インストールとセットアップ (Installation & Setup)

### ① パッケージのインストール
```bash
pip install edd-agent-tools
```

### ② 初期セットアップと LLM 認証
Gemini API を使用するためのクライアント種別の切り替え、およびローカルの Antigravity CLI (`agy`) と接続して開発用クレジットを共有するための手動ログイン手順については、**[SETUP.md](SETUP.md)** を参照してセットアップを完了させてください。

---

## 4. AI エージェントとの連携 (Model Context Protocol)

### 登録設定例 (`~/.gemini/config/mcp.json` 等)
`uv` ツールランナー（推奨）を使用する場合、以下の設定を追加するだけで、事前インストール不要で MCP サーバーが一撃起動します。

```json
{
  "mcpServers": {
    "edd-agent-tools": {
      "command": "uvx",
      "args": [
        "--from",
        "edd-agent-tools",
        "edd-agent-mcp"
      ]
    }
  }
}
```

*   **公開リソース (URI)**:
    *   `edd://docs/test_architecture`: テスト設計仕様・Protocol規約
    *   `edd://docs/eval_design`: サンドボックス隔離・アサーションポリシー
    *   `edd://rules/agents`: エージェントが遵守すべき厳密ルール（`AGENTS.md`）
*   ※ 詳細な設定オプションや仮想環境内のパスを指定する方法については、**[SETUP.md の MCP 連携セクション](SETUP.md#4-ローカル-mcp-サーバーのセットアップと-antigravity-連携)** を参照してください。

---

## 5. 前提条件と動作環境 (Prerequisites)

本ライブラリは、Pydanticモデルの `StrEnum` などの機能を使用しているため、以下の環境が必要です。
*   **Python**: `>= 3.11` (Python 3.11 以上を必須とします)
