import os
from edd_agent_tools.skills import Skill
from edd_agent_tools import LibraryDocumentationReader

class DesignPrompter:
    """
    スキル設計のためのプロンプト構築ロジックを提供します。
    """
    def __init__(self, designer_skill: Skill):
        self._designer_skill = designer_skill
        self._skeleton_tmpl = self._designer_skill.load_asset("design_skeleton_template.txt")
        self._mapping_tmpl = self._designer_skill.load_asset("design_mapping_template.txt")

    def build_l1_request(
        self, 
        client,
        prompt: str, 
        existing_name: str | None, 
        existing_constraints: str, 
        l1_skills_context: str,
        scan_target: str | None,
        output_dir: str | None,
        existing_design_file_path: str | None = None
    ):
        """
        第 1 段階 (L1骨組み設計) 用の GeminiRequest を構築します。
        """
        existing_name_str = existing_name or "なし"
        formatted_prompt = self._skeleton_tmpl.format(
            existing_name=existing_name_str,
            prompt=prompt,
            existing_constraints=existing_constraints,
            l1_skills_context=l1_skills_context
        )

        request = client.request(formatted_prompt)
        if scan_target:
            ref_root = output_dir if output_dir else os.path.dirname(scan_target)
            request.add_dir(scan_target, ref_root=ref_root, file_filter=lambda p: p.endswith(".py"))
            
        # 既存の design.json があれば LLM に対し参考コンテキストとして添付提供する
        if existing_design_file_path and os.path.exists(existing_design_file_path):
            request.add_file(existing_design_file_path, ref_root=output_dir)
            
            
        # プロジェクト共通規約（README.md）をコンテキストに添付
        try:
            reader = LibraryDocumentationReader(library_name="edd_agent_tools")
            docs_content = reader.read_documentation()
            request.add_text(f"=== プロジェクト共通開発規約 ===\n{docs_content}")
        except Exception as e:
            print(f"Info: Could not load README.md in designer: {e}")
            
        return request

    def build_l2_request(
        self,
        client,
        skeleton_design_str: str,
        l2_skills_context: str
    ):
        """
        第 2 段階 (L2引数マッピング) 用の GeminiRequest を構築します。
        """
        formatted_prompt = self._mapping_tmpl.format(
            skeleton_design_str=skeleton_design_str,
            l2_skills_context=l2_skills_context
        )
        return client.request(formatted_prompt)