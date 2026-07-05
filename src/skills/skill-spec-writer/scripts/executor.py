from google.adk.tools import ToolContext
from .models import Input, Output
from .spec_generator import SpecGenerator # SpecGenerator をインポート

class SkillExecutor:
    """
    ビジネスロジックを責務ごとに分割して実行するオブジェクト指向エグゼキューター。
    """
    def __init__(self, params: Input, tool_context: ToolContext):
        self.params = params
        self.tool_context = tool_context

    def execute(self) -> Output:
        generator = SpecGenerator(self.params, self.tool_context)
        return generator.generate()


