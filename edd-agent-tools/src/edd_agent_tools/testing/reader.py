import os
import sys

class LibraryDocumentationReader:
    """エージェントが特定のパッケージのLLM向け開発規約・API仕様ドキュメントを動的にロードするためのリファレンスブック・ツール"""
    
    def __init__(self, library_name: str = "edd_agent_tools"):
        self.library_name = library_name

    def __call__(self, target_library: str = "edd_agent_tools") -> str:
        """
        指定されたライブラリ（edd_agent_toolsなど）のLLM向け公式開発規約やAPI仕様のドキュメントを動的にロードします。
        新規コードの実装や修正を開始する前に、必ずこのツールを実行して最新のAPI仕様や状態管理（state）のルールを確認してください。
        """
        if target_library != self.library_name:
            return f"Error: No documentation available for library '{target_library}'."
            
        try:
            from importlib import resources
            if hasattr(resources, "files"):
                return resources.files("edd_agent_tools.docs").joinpath("instructions.md").read_text(encoding="utf-8")
            else:
                return resources.read_text("edd_agent_tools.docs", "instructions.md")
        except Exception as e:
            return f"Error loading documentation: {e}"
