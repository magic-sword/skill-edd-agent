from google.adk.tools import ToolContext
from .models import Input, Output

class SkillExecutor:
    """ビジネスロジックを責務ごとに分割して実行するオブジェクト指向エグゼキューター。

    Args:
        params: 呼び出し元から渡された型安全な入力パラメータ。
        tool_context: ADKのセッション状態などを管理するコンテキスト。
    """
    def __init__(self, params: Input, tool_context: ToolContext):
        self.params = params
        self.tool_context = tool_context

    def execute(self) -> Output:
        """ビジネスロジックを実行し、結果を返します。

        Returns:
            処理結果の構造化データ（Output）。

        Raises:
            NotImplementedError: ロジックが未実装の場合。
        """
        from .client import SkillsStateClient
        from .skill_validator import SkillValidator

        # 1. SkillsStateClientのインスタンスを作成
        skills_state_client = SkillsStateClient(self.tool_context)

        # 2. SkillValidatorのインスタンスを作成し、クライアントを渡す
        skill_validator = SkillValidator(skills_state_client)

        # 3. スキルの動的ロード検証を実行
        status, details = skill_validator.validate_skill_import(self.params.skill)

        # 4. 結果をOutputモデルにマッピングして返却
        return Output(status=status, details=details)
