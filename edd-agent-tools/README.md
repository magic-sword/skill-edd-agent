# edd-agent-tools

EDD（評価駆動開発）による自律型 AI エージェントおよび Anthropic 標準（Markdown-First & Progressive Disclosure）スキルの開発・運用をサポートするための共通基盤ライブラリ。

---

## 1. 主な機能と特徴

*   **Markdown-First & Progressive Disclosure 3層リソース管理 (`Skill`, `SkillSpec`)**
    `SKILL.md` を単一真実源とし、`scripts/`（実行用）、`references/`（知識用）、`assets/`（素材用）の3層分離を安全にロード・管理するドメインクラスを提供。
*   **4段階品質保証パイプライン & 決定論的レンダラー (`SkillTemplateEngine`, `SkillValidator`)**
    Pydanticモデル（`SkillLogicDraft`）からの決定論的 `SKILL.md` レンダリング、および構文・実在整合性・Imperative文体を検査する静的バリデータを提供。
*   **Gymnasium 互換サンドボックス隔離環境 (`WorkspaceEnvProtocol`, `LocalWorkspaceEnv`)**
    コードやテスト実行による環境破壊を防ぐため、仮想環境と Git ロールバック機能を提供。
*   **動的ディスパッチテストフレームワーク (`TestGenerator` / `TestExecutor` / `ContractTestRunner`)**
    テストケースの「生成」と「実行」をプロトコルに基づいて完全に分離し、再現可能なペアリングテストを実現。
*   **Gemini API クライアント & Strict JSON Schema 自動正規化 (`GeminiClient`, `GeminiRequest`)**
    OpenAPI 3.0 Strict Mode に適合した再帰的 `$defs` インライン解決と指数バックオフリトライを内蔵。
*   **FastMCP サーバー統合 (`edd-agent-mcp`)**
    AIエージェントに対し、設計規約（`edd://guidelines/*`）や静的検証ツール（`edd_validate_skill`, `edd_init_skill`）をオンデマンド提供。

---

## 2. 詳細設計書インデックス (Detailed Documents)

*   **[progressive_disclosure.md](src/edd_agent_tools/docs/progressive_disclosure.md)**: 3層リソース分離とProgressive Disclosure標準規約。
*   **[prompt_syntax.md](src/edd_agent_tools/docs/prompt_syntax.md)**: Imperative文体規約とFrontmatter仕様。
*   **[skill_patterns.md](src/edd_agent_tools/docs/skill_patterns.md)**: 4大スキルパターンの設計ガイド。
*   **[design_philosophy.md](src/edd_agent_tools/docs/design_philosophy.md)**: 全体設計思想・フォルダ構成規約。
*   **[test_architecture.md](src/edd_agent_tools/docs/test_architecture.md)**: テストの Generator-Executor ペアリングパターンの標準 Protocol 仕様。

---

## 3. インストールと CLI

```bash
pip install -e edd-agent-tools

# CLIコマンド
python -m edd_agent_tools.skills.cli init my-skill --pattern workflow
python -m edd_agent_tools.skills.cli validate src/skills/my-skill
python -m edd_agent_tools.skills.cli package src/skills/my-skill
```
