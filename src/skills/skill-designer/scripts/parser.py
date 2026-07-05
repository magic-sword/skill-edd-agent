from edd_agent_tools.registry import SkillRegistry
from edd_agent_tools.parser import PydanticModelParser

class ConstraintParser:
    """
    既存スキルの制約事項をパースして抽出するロジックを提供します。
    """
    def __init__(self):
        self._registry = SkillRegistry()

    def get_existing_constraints(self, skill_name: str | None) -> str:
        """
        指定されたスキル名から既存の制約事項を抽出し、文字列として返します。

        Args:
            skill_name: 既存のスキル名。

        Returns:
            既存の制約事項の文字列。存在しない場合は「なし」。
        """
        existing_constraints_str = "なし"
        if skill_name:
            try:
                skill_obj = self._registry.get_skill(skill_name)
                skill_module = skill_obj.load() if skill_obj else None
                InputSchema = getattr(skill_module, "Input", None) if skill_module else None
                if InputSchema:
                    extracted = PydanticModelParser.parse_constraints(InputSchema)
                    if extracted:
                        existing_constraints_str = "\n".join(f"- {c}" for c in extracted)
            except Exception as e:
                # ログ出力は呼び出し元で行うため、ここでは簡易的な出力に留めるか、raise するかを検討
                # 今回は呼び出し元で Info ログが出ているのでそれに合わせる。
                print(f"Info: Could not load handler.py for validator constraint parsing in designer: {e}")
        return existing_constraints_str
