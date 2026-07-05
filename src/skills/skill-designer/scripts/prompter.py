import os
from edd_agent_tools.registry import SkillRegistry
from edd_agent_tools.gemini import GeminiContentBuilder
from edd_agent_tools.docs import LibraryDocumentationReader
from google.genai import types

class DesignPrompter:
    """
    スキル設計のためのプロンプト構築ロジックを提供します。
    """
    def __init__(self):
        self._registry = SkillRegistry()
        designer_dir = self._registry.get_skill_directory("skill-designer")
        self._prompt_tmpl = designer_dir.load_asset("prompt.txt")

    def build_contents(
        self, 
        requirement: str, 
        existing_name: str | None, 
        existing_constraints: str, 
        scan_target: str | None,
        output_dir: str | None
    ) -> list[types.ContentType]:
        """
        Gemini API に送信するためのマルチパートコンテンツを構築します。

        Args:
            requirement: 設計するスキルの機能要件。
            existing_name: 既存のスキル名。
            existing_constraints: 既存の制約事項。
            scan_target: ソースコードのスキャン対象ディレクトリ。
            output_dir: 生成されたdesign.jsonを保存するディレクトリのパス。

        Returns:
            Gemini API に送信するためのマルチパートコンテンツのリスト。
        """
        existing_name_str = existing_name or "なし"
        formatted_prompt = self._prompt_tmpl.format(
            existing_name=existing_name_str,
            requirement=requirement,
            existing_constraints=existing_constraints
        )

        builder = GeminiContentBuilder(formatted_prompt)
        if scan_target:
            ref_root = output_dir if output_dir else os.path.dirname(scan_target)
            builder.add_dir(scan_target, ref_root=ref_root, file_filter=lambda p: p.endswith(".py"))
            
        # プロジェクト共通規約（README.md）をコンテキストに添付
        try:
            reader = LibraryDocumentationReader(library_name="edd_agent_tools")
            docs_content = reader.read_documentation()
            builder.parts.append(f"=== プロジェクト共通開発規約 ===\n{docs_content}")
        except Exception as e:
            print(f"Info: Could not load README.md in designer: {e}")
            
        return builder.build()
