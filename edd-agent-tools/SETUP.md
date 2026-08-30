# edd-agent-tools 環境セットアップガイド

本ドキュメントでは、`edd-agent-tools` パッケージの開発・利用に必要な環境セットアップ手順および MCP サーバー連携について記述します。

---

## 1. 前提条件

* Python 3.11 以上
* pip / venv または devcontainer 環境

---

## 2. インストール手順

### ローカル開発モード (Editable Install)
リポジトリのルートまたは `edd-agent-tools` ディレクトリから以下を実行します：

```bash
pip install -e edd-agent-tools
```

正常にインストールされたか確認します：
```bash
edd --help
```

---

## 3. FastMCP サーバーの利用 (`edd-agent-mcp`)

`edd-agent-tools` は、Claude Code, Antigravity IDE, Cursor 等の外部エージェント向けに FastMCP サーバーを提供しています。

### MCP サーバーの起動
```bash
edd-agent-mcp
```

### 提供リソース & ツール
* **リソース (`edd://...`)**:
  * `edd://rules/agents`: エージェント開発制約（SSOT）
  * `edd://guidelines/progressive-disclosure`: 3層リソース分離規約
  * `edd://docs/*`: 各種アーキテクチャ設計書
* **ツール**:
  * `edd_validate_skill`: スキルの静的リンター検証
  * `edd_init_skill`: スキル雛形ディレクトリの初期化

---

## 4. テストの実行

```bash
pytest tests/ -v
```
