# 必須行動規範: 作業開始時の設計思想確認 (Mandatory Initial Orientation)

## 1. 目的
本プロジェクト（Self-Evolving EDD Agent）において、AI エージェントが勝手な推測や古い知識でコードを変更することを防ぎ、最新の Two-Tier アーキテクチャおよび規約駆動設計に従って一貫した開発を行うためのルールです。

## 2. 必須ルール
すべての AI エージェントは、タスクに着手する前に**必ず最初に関連設計思想ドキュメントまたは MCP リソースを確認**し、全体像を把握した上で作業を開始してください。

### ① MCP 経由の確認（推奨）
FastMCP サーバー（`edd-agent-mcp`）が提供する以下のリソースを優先的に読み込んでください：
- `edd://docs/design_philosophy` : 中核設計思想、Two-Tier 疎結合分離、カスケード解決、Prerequisites 照合方針
- `edd://rules/agents` : プラットフォーム不変契約および変更可能領域（Mutable Zone）の定義
- `edd://guidelines/progressive_disclosure` : 3層リソース分離（scripts/references/assets）規約
- `edd://docs/test_architecture` : 統合評価テストハーネスと CLI-as-an-API 契約

### ② ローカルファイル経由の確認
MCP が利用できない環境では、以下の SSOT ファイルを直接参照してください：
- [`edd-agent-tools/src/edd_agent_tools/docs/design_philosophy.md`](file:///workspace/edd-agent-tools/src/edd_agent_tools/docs/design_philosophy.md)
- [`edd-agent-tools/src/edd_agent_tools/AGENTS.md`](file:///workspace/edd-agent-tools/src/edd_agent_tools/AGENTS.md)
- [`.agents/AGENTS.md`](file:///workspace/.agents/AGENTS.md)
