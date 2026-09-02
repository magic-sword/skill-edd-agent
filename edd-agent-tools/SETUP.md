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
  * `edd://guidelines/progressive_disclosure`: 3層リソース分離規約
  * `edd://guidelines/prompt_syntax`: Imperative文体・Frontmatter規約
  * `edd://guidelines/skill_patterns`: 4大スキルパターン設計ガイド
  * `edd://docs/*`: 各種アーキテクチャ設計書 (`design_philosophy`, `test_architecture`, `eval_design`, `sandbox_design`)
* **ツール**:
  * `edd_validate_skill`: スキルの静的リンター検証
  * `edd_init_skill`: スキル雛形ディレクトリの初期化

---

## 4. LLM-as-a-Judge 評価の設定 (任意)

Google ADK 2.0 純正の LLM-as-a-Judge 評価（Gemini 2.5 Flash）を実行する場合は、以下の環境変数を設定してください（未設定時は決定論的ルールベース評価へ自動フォールバックします）：

```bash
export GEMINI_API_KEY="your-gemini-api-key"
# または
export GOOGLE_API_KEY="your-google-api-key"
```

---

## 5. テストスイートの実行

```bash
# 全テストの実行 (49件すべて Green)
pytest tests/ -v

# ADK 評価および Trajectory 統合テスト
pytest tests/test_adk_eval_integration.py -v

# 自己進化 End-to-End デモの実行
python demo_self_evolution.py
```
