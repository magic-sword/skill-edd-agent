# edd-agent-tools

EDD（評価駆動開発）による自律型 AI エージェントおよび Anthropic 標準（Markdown-First & Progressive Disclosure）スキルの開発・運用をサポートするためのフルスタック基盤ライブラリ。

---

## 1. 主な機能と特徴

*   **Clean Layered Architecture (`core`, `validation`, `packaging`, `evaluation`, `adk`, `mcp`, `cli`)**
    単一真実源のドメインモデル（`core` / `Skill`, `SkillTests`, `SkillsState`）、AST静的検証リンター（`validation` / `SkillValidator`）、ZIPパッケージング＆スキャフォールド（`packaging` / `SkillPackager`, `SkillScaffolder`）、契約テスト・多層評価・診断・自己修復（`evaluation`）、Google ADK 2.0 連携（`adk` / `EddSkillToolset`）、FastMCP 連携（`mcp`）、統合 CLI（`cli`）を明確に責務分離。
*   **Markdown-First & Progressive Disclosure 3層リソース管理 (`Skill`, `SkillSpec`, `SkillsState`)**
    `SKILL.md` を単一真実源とし、`scripts/`（実行用）、`references/`（知識用）、`assets/`（素材用）の3層分離を安全にロード・管理するドメインクラスと DAG 依存関係グラフ検証を提供。他プロジェクトへの配布時にもパスに依存しない Zero-Hardcoding 設計。
*   **4段階品質保証パイプライン & 決定論的検証 (`SkillValidator`, `SkillPackager`, `SkillScaffolder`)**
    Pydanticモデル（`SkillLogicDraft`）からの決定論的レンダリング、`src/skills/skill-creator/assets/templates/` を SSOT とするテンプレート展開、および構文・実在整合性・Imperative文体を検査する静的バリデータを提供。
*   **Gymnasium 互換サンドボックス隔離環境 (`WorkspaceEnvProtocol`, `LocalWorkspaceEnv`)**
    コードやテスト実行による環境破壊を防ぐため、仮想環境と Git ロールバック機能を提供。
*   **多層EDD評価フレームワーク & Tier昇格ゲートキーパー (`ContractTestRunner`, `SimulationEvalRunner`, `CascadeTestRunner`)**
    契約テスト、トリガー精度テスト、ゴールデン出力評価、および上位ワークフローへの連鎖回帰テストを一元管理する決定論的評価エンジンを提供。
*   **失敗診断 & 自己進化エンジン (`SkillDiagnoser`, `SkillOptimizer`)**
    テスト失敗ログを構造的に解析し、根本原因（spec / script / test / reference）の特定と自律的な修復ループ・Tier昇格を実現。
*   **Google ADK 2.0 ネイティブ統合 (`EddSkillToolset`, `create_adk_skill_toolset`) & FastMCP サーバー (`edd-agent-mcp`)**
    Google ADK の Progressive Disclosure ライフサイクルおよび Claude Code / Antigravity IDE 向け MCP リソース・ツールを提供。

---

## 2. 詳細設計書インデックス (Detailed Documents)

*   **[progressive_disclosure.md](src/edd_agent_tools/docs/progressive_disclosure.md)**: 3層リソース分離とProgressive Disclosure標準規約。
*   **[prompt_syntax.md](src/edd_agent_tools/docs/prompt_syntax.md)**: Imperative文体規約とFrontmatter仕様。
*   **[skill_patterns.md](src/edd_agent_tools/docs/skill_patterns.md)**: 4大スキルパターンの設計ガイド。
*   **[design_philosophy.md](src/edd_agent_tools/docs/design_philosophy.md)**: 全体設計思想・フォルダ構成規約。
*   **[test_architecture.md](src/edd_agent_tools/docs/test_architecture.md)**: テストの Generator-Executor ペアリングパターンの標準 Protocol 仕様。
*   **[eval_design.md](src/edd_agent_tools/docs/eval_design.md)**: 仮想環境サンドボックスとシミュレーション評価の設計思想。

---

## 3. インストールと統合 CLI (`edd`)

```bash
pip install -e edd-agent-tools

# 統合 CLI (edd) - 動的ディスパッチによるスキルの直接実行
edd run case-converter --input "hello_world" --format camel
# またはスキル名を直接サブコマンドとして指定可能 (Git プラグイン方式)
edd case-converter --input "hello_world" --format camel

# スキルライフサイクル管理
edd init my-skill --pattern workflow
edd validate src/skills/my-skill
edd package src/skills/my-skill --out dist
edd list

# EDD 多層評価・Tier 昇格・失敗診断・一括最適化
edd eval my-skill --type all
edd tier-gate my-skill --tier 1
edd diagnose my-skill
edd optimize my-skill --tier 1

# MCP サーバー起動
edd-agent-mcp
```
