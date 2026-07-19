import os
import sys

class LibraryDocumentationReader:
    """開発エージェントが、対象パッケージのシステム制約ルール（AGENTS.md）を動的にロードするためのドキュメントリーダー。
    
    シングルソースの原則に基づき、パッケージ同梱のルールファイルをメモリ上にロードしてプロンプト等に挿入します。
    """
    
    def __init__(self, library_name: str = "edd_agent_tools"):
        """LibraryDocumentationReader を初期化します。

        Args:
            library_name: ロード対象のライブラリ名（デフォルト: 'edd_agent_tools'）。
        """
        self.library_name = library_name

    def read_documentation(self, target_library: str = "edd_agent_tools") -> str:
        """指定されたライブラリのLLM向け公式開発規約やシステム制約（AGENTS.md）を動的にロードします。

        Args:
            target_library: ロード対象のライブラリ名。デフォルトは 'edd_agent_tools'。

        Returns:
            ロードされた Markdown ドキュメントのテキストコンテンツ。
        """
        if target_library != self.library_name:
            return f"Error: No documentation available for library '{target_library}'."
            
        # 1. 開発環境およびパッケージ内の AGENTS.md ロード
        try:
            import importlib.resources
            ref = importlib.resources.files("edd_agent_tools").joinpath("AGENTS.md")
            if ref.exists():
                return ref.read_text(encoding="utf-8")
        except Exception:
            pass
            
        # 2. フォールバック（相対パスでの直接探索）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fallback_path = os.path.join(current_dir, "AGENTS.md")
        if os.path.exists(fallback_path):
            try:
                with open(fallback_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return f"Error loading fallback documentation: {e}"
                
        return "Error: Documentation file (AGENTS.md) not found."

