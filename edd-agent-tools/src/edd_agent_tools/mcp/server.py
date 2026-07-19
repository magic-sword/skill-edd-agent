import importlib.resources
from mcp.server.fastmcp import FastMCP

def create_mcp_server() -> FastMCP:
    """MCPサーバーのインスタンスを遅延生成し、リソース定義をバインドします。
    
    インポート時の副作用（デッドロックや初期化遅延）を排除するため、起動時に明示的に呼び出されます。
    """
    mcp = FastMCP("edd-agent-tools")

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
        """Gymnasium 互換サンドボックス（WorkspaceEnvProtocol）の隔離設計およびテストの合否アサーション判定論理のドキュメントを取得します。"""
        try:
            ref = importlib.resources.files("edd_agent_tools.docs").joinpath("eval_design.md")
            return ref.read_text(encoding="utf-8")
        except Exception as e:
            raise FileNotFoundError(f"Error: Failed to load eval_design.md: {e}")

    @mcp.resource("edd://docs/design_philosophy")
    def get_design_philosophy() -> str:
        """ADK 2.0 スキル定義規約、カプセル化コア思想、およびフォルダ構成規約ドキュメントを取得します。"""
        try:
            ref = importlib.resources.files("edd_agent_tools.docs").joinpath("design_philosophy.md")
            return ref.read_text(encoding="utf-8")
        except Exception as e:
            raise FileNotFoundError(f"Error: Failed to load design_philosophy.md: {e}")

    @mcp.resource("edd://docs/sandbox_design")
    def get_sandbox_design() -> str:
        """Gymnasium 互換サンドボックスの隔離実行（DI）詳細と、CLI ランナーの引数仕様ドキュメントを取得します。"""
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

    return mcp

def main():
    """標準入出力を介して MCP サーバーを起動します。"""
    server = create_mcp_server()
    server.run()

if __name__ == "__main__":
    main()
