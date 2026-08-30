# プロジェクト開発ルール (Workspace Entry Point)

本プロジェクトでは、開発基盤パッケージ `edd-agent-tools` を**単一真実源（Single Source of Truth: SSOT）**として採用しています。

---

## 1. 単一真実源（SSOT）と開発規約の参照
* **エージェント開発制約の真実源**:
  エージェント向けの開発制約、Two-Tier Architecture、Progressive Disclosure、および4段階品質保証パイプラインはすべて [`edd-agent-tools/AGENTS.md`](file:///workspace/edd-agent-tools/src/edd_agent_tools/AGENTS.md) に定義されています。
* **MCP によるオンデマンド参照**:
  開発規約や設計ガイドラインは FastMCP サーバー（`edd-agent-mcp`）のリソース（`edd://rules/agents`, `edd://guidelines/*`, `edd://docs/*`）からも参照可能です。

## 2. 開発パッケージの利用 (`edd-agent-tools`)
* **基盤パッケージの活用**:
  スキルの探索・パス解決（`SkillsState`）、サンドボックス環境（`LocalWorkspaceEnv`）、多層評価・Tier昇格（`ContractTestRunner`, `SimulationEvalRunner`）、静的検証（`SkillValidator`）等の共通基盤ロジックはすべて `edd-agent-tools` を利用し、各スキル内で重複実装しないでください。
* **二重 LLM 呼び出しの禁止**:
  スキル内のスクリプト内部で LLM API を直接叩くバッチ処理を作らず、エージェント自身が `SKILL.md` の指示に従って対話・推論を行う設計としてください。
* **ローカルインストール**:
  本パッケージは `pip install -e edd-agent-tools` でインストールして開発してください。

## 3. コード品質とシンプルさの徹底
* **ボイラープレートの排除**: 不要な抽象化レイヤーやモンキーパッチを作らず、フラットで簡潔な実装を維持してください。
* **不要ファイルの即時削除**: リファクタリングによって不要になったファイルや重複関数は速やかに削除し、コードベース内のノイズを排除してください。