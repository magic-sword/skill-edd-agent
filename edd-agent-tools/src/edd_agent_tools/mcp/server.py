import importlib.resources
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from edd_agent_tools.validation.validator import SkillValidator
from edd_agent_tools.packaging.scaffold import SkillScaffolder

def create_mcp_server() -> FastMCP:
    """MCPサーバーのインスタンスを遅延生成し、リソース定義とツールをバインドします。"""
    mcp = FastMCP("edd-agent-tools")

    # ==========================================
    # Guidelines Resources
    # ==========================================

    @mcp.resource("edd://guidelines/progressive_disclosure")
    def get_progressive_disclosure_guidelines() -> str:
        """3層リソース分離（scripts, references, assets）と Progressive Disclosure の標準規約を取得します。"""
        try:
            ref = importlib.resources.files("edd_agent_tools.docs").joinpath("progressive_disclosure.md")
            return ref.read_text(encoding="utf-8")
        except Exception as e:
            raise FileNotFoundError(f"Error: Failed to load progressive_disclosure.md: {e}")

    @mcp.resource("edd://guidelines/prompt_syntax")
    def get_prompt_syntax_guidelines() -> str:
        """SKILL.md および指示プロンプトにおける Imperative（動詞起点・客観的）記法と Frontmatter 規約を取得します。"""
        try:
            ref = importlib.resources.files("edd_agent_tools.docs").joinpath("prompt_syntax.md")
            return ref.read_text(encoding="utf-8")
        except Exception as e:
            raise FileNotFoundError(f"Error: Failed to load prompt_syntax.md: {e}")

    @mcp.resource("edd://guidelines/skill_patterns")
    def get_skill_patterns_guidelines() -> str:
        """4大スキル構造パターン（workflow, task_based, reference, capabilities）の設計ガイドを取得します。"""
        try:
            ref = importlib.resources.files("edd_agent_tools.docs").joinpath("skill_patterns.md")
            return ref.read_text(encoding="utf-8")
        except Exception as e:
            raise FileNotFoundError(f"Error: Failed to load skill_patterns.md: {e}")

    @mcp.resource("edd://docs/design_philosophy")
    def get_design_philosophy() -> str:
        """スキル設計思想、単一真実源原則、およびフォルダ構成規約ドキュメントを取得します。"""
        try:
            ref = importlib.resources.files("edd_agent_tools.docs").joinpath("design_philosophy.md")
            return ref.read_text(encoding="utf-8")
        except Exception as e:
            raise FileNotFoundError(f"Error: Failed to load design_philosophy.md: {e}")

    @mcp.resource("edd://docs/test_architecture")
    def get_test_architecture() -> str:
        """テストケースの生成・実行スキルを開発する際の実装制約、DIモデル、およびProtocol仕様ドキュメントを取得します。"""
        try:
            ref = importlib.resources.files("edd_agent_tools.docs").joinpath("test_architecture.md")
            return ref.read_text(encoding="utf-8")
        except Exception as e:
            raise FileNotFoundError(f"Error: Failed to load test_architecture.md: {e}")

    @mcp.resource("edd://docs/eval_design")
    def get_eval_design() -> str:
        """多層EDD評価フレームワーク、アサーション設計、およびシミュレーション評価仕様を取得します。"""
        try:
            ref = importlib.resources.files("edd_agent_tools.docs").joinpath("eval_design.md")
            return ref.read_text(encoding="utf-8")
        except Exception as e:
            raise FileNotFoundError(f"Error: Failed to load eval_design.md: {e}")

    @mcp.resource("edd://docs/sandbox_design")
    def get_sandbox_design() -> str:
        """決定論的サンドボックス仮想環境、ロールバック仕様、およびCLI実行環境ドキュメントを取得します。"""
        try:
            ref = importlib.resources.files("edd_agent_tools.docs").joinpath("sandbox_design.md")
            return ref.read_text(encoding="utf-8")
        except Exception as e:
            raise FileNotFoundError(f"Error: Failed to load sandbox_design.md: {e}")

    @mcp.resource("edd://rules/agents")
    def get_agents_rules() -> str:
        """本パッケージを使用・拡張するAIエージェントが厳密に遵守すべきシステム制約ルールを取得します。"""
        try:
            ref = importlib.resources.files("edd_agent_tools").joinpath("AGENTS.md")
            return ref.read_text(encoding="utf-8")
        except Exception as e:
            raise FileNotFoundError(f"Error: Failed to load AGENTS.md: {e}")

    # ==========================================
    # Management Tools
    # ==========================================

    @mcp.tool("edd_validate_skill")
    def mcp_validate_skill(skill_dir: str) -> dict:
        """指定されたスキルディレクトリが Markdown-First / Progressive Disclosure 規約に準拠しているか静的検証します。"""
        result = SkillValidator.validate_directory(skill_dir)
        return result.model_dump()

    @mcp.tool("edd_init_skill")
    def mcp_init_skill(name: str, path: str = ".", pattern: str = "workflow") -> str:
        """指定された場所に新しいスキル雛形ディレクトリを初期化します。"""
        try:
            target = SkillScaffolder.scaffold(name, output_base_dir=path, pattern=pattern)
            return f"Successfully initialized skill '{name}' at {target}"
        except Exception as e:
            return f"Failed to initialize skill '{name}': {e}"

    return mcp

def main():
    """標準入出力を介して MCP サーバーを起動します。"""
    server = create_mcp_server()
    server.run()

if __name__ == "__main__":
    main()
