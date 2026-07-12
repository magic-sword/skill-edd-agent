from .models import Output
from .spec_generator import SpecGenerator

class SkillExecutor:
    """
    ビジネスロジックを責務ごとに分割して実行するオブジェクト指向エグゼキューター。
    """
    def __init__(self, design_path: str = None, skill: str = None, output_dir: str = None, source_code_dir: str = None, prompt: str = None):
        # models.py で定義される Input クラスの代わりとして、引数を個別に受け取る
        from .models import Input
        self.params = Input(
            design_path=design_path,
            skill=skill,
            output_dir=output_dir,
            source_code_dir=source_code_dir,
            prompt=prompt
        )

    def execute(self) -> Output:
        generator = SpecGenerator(self.params)
        return generator.generate()
