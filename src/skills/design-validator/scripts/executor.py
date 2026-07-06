from google.adk.tools import ToolContext
from .models import Input, Output
from .validator import DesignValidator # validator をインポート

class SkillExecutor:
    """ビジネスロジックを責務ごとに分割して実行するオブジェクト指向エグゼキューター。

    Args:
        params: 呼び出し元から渡された型安全な入力パラメータ。
        tool_context: ADKのセッション状態などを管理するコンテキスト。
    """
    def __init__(self, params: Input, tool_context: ToolContext):
        self.params = params
        self.tool_context = tool_context
        # DesignValidator を初期化
        self._validator = DesignValidator(tool_context=self.tool_context)


    def execute(self) -> Output:
        """
        ビジネスロジックを実行し、結果を返します。

        Returns:
            処理結果の構造化データ（Output）。
        """
        # DesignValidator を使用してスキルを検証
        return self._validator.validate_skill(skill_name=self.params.skill)
