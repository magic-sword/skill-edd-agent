import os
from edd_agent_tools.registry import SkillRegistry
from edd_agent_tools.docs import LibraryDocumentationReader
from google.genai import types
from edd_agent_tools.directory import SkillDirectory # SkillDirectoryをインポート

class DesignPrompter:
    """
    スキル設計のためのプロンプト構築ロジックを提供します。
    """
    def __init__(self, designer_directory: SkillDirectory):
        self._designer_directory = designer_directory
        self._prompt_tmpl = self._designer_directory.load_asset("design_instruction_template.txt")

    def build_request(
        self, 
        client,
        prompt: str, 
        existing_name: str | None, 
        existing_constraints: str, 
        scan_target: str | None,
        output_dir: str | None
    ):
        """
        GeminiRequest オブジェクトを構築します。
        """
        existing_name_str = existing_name or "なし"
        formatted_prompt = self._prompt_tmpl.format(
            existing_name=existing_name_str,
            prompt=prompt,
            existing_constraints=existing_constraints
        )

        request = client.request(formatted_prompt)
        if scan_target:
            ref_root = output_dir if output_dir else os.path.dirname(scan_target)
            request.add_dir(scan_target, ref_root=ref_root, file_filter=lambda p: p.endswith(".py"))
            
        # プロジェクト共通規約（README.md）をコンテキストに添付
        try:
            reader = LibraryDocumentationReader(library_name="edd_agent_tools")
            docs_content = reader.read_documentation()
            request.add_text(f"=== プロジェクト共通開発規約 ===\n{docs_content}")
        except Exception as e:
            print(f"Info: Could not load README.md in designer: {e}")
            
        return request