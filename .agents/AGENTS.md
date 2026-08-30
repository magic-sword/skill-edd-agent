# プロジェクト開発ルール (Workspace Entry Point)

本プロジェクトの究極の目的は、**「AI エージェントが自らのスキル（手順書・ドメイン知識・決定論的スクリプト）を自律的にテスト・診断・修復・進化させる自己進化システム（Self-Evolving Agentic Ecosystem）」** の構築です。
一般的な DRY 原則よりも **「エージェント自己改善の局所性（Locality）と安全な隔離（Isolation）」** を最上位の原則として優先します。

開発基盤パッケージ `edd-agent-tools` を**単一真実源（Single Source of Truth: SSOT）**として採用しています。

---

## 1. 単一真実源（SSOT）と開発規約の参照
* **エージェント開発制約の真実源**:
  エージェント向けの開発制約、Two-Tier Architecture、Progressive Disclosure、および4段階品質保証パイプラインはすべて [`edd-agent-tools/AGENTS.md`](file:///workspace/edd-agent-tools/src/edd_agent_tools/AGENTS.md) に定義されています。
* **MCP によるオンデマンド参照**:
  開発規約や設計ガイドラインは FastMCP サーバー（`edd-agent-mcp`）のリソース（`edd://rules/agents`, `edd://guidelines/*`, `edd://docs/*`）からも参照可能です。

## 2. パッケージとスキルの責務分離と自己改善隔離
* **個別ロジックのスキル内隔離 (Self-Contained Skill Isolation)**:
  スキルの個別処理スクリプト（`scripts/`）、ドメインスキーマ（`references/`）、出力用テンプレート（`assets/`）、個別契約テスト（`tests/`）は、エージェントが安全かつ局所的に自己改善（Self-Evolution）できるように、必ずスキルディレクトリ内に隔離して実装してください。
* **過度なパッケージ集約の禁止 (Anti-Pattern: Excessive Centralization)**:
  スキル固有の個別処理を「共通化できる」という理由だけで pip パッケージ（`edd-agent-tools`）へ過度に移転・集約してはなりません。
* **基盤パッケージの活用 (`edd-agent-tools`)**:
  サンドボックス環境（`LocalWorkspaceEnv`）、多層評価・Tier昇格（`ContractTestRunner`, `SimulationEvalRunner`）、静的検証（`SkillValidator`）、スキル探索（`SkillsState`）等の共通不変プラットフォームは `edd-agent-tools` を利用してください。
* **二重 LLM 呼び出しの禁止**:
  スキル内のスクリプト内部で LLM API を直接叩くバッチ処理を作らず、エージェント自身が `SKILL.md` の指示に従って対話・推論を行う設計としてください。
* **ローカルインストール**:
  本パッケージは `pip install -e edd-agent-tools` でインストールして開発してください。

## 3. コード品質とシンプルさの徹底
* **ボイラープレートの排除**: 不要な抽象化レイヤーやモンキーパッチを作らず、フラットで簡潔な実装を維持してください。
* **不要ファイルの即時削除**: リファクタリングによって不要になったファイルや重複関数は速やかに削除し、コードベース内のノイズを排除してください。