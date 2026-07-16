from typing import Any
from .models import GenerateSkillSpecOutput
from .spec_generator import SpecGenerator


class SkillExecutor:
    """
    ビジネスロジックを責務ごとに分割して実行するオブジェクト指向エグゼキューター。
    """

    def __init__(self):
        pass

    def generate_skill_spec(self, design_path: str | None = None, skill: str | None = None, output_dir: str | None = None, source_code_dir: str | None = None, prompt: str | None = None) -> GenerateSkillSpecOutput:
        generator = SpecGenerator(
            design_path=design_path,
            skill=skill,
            output_dir=output_dir,
            source_code_dir=source_code_dir,
            prompt=prompt
        )
        return generator.generate()
