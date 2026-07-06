from google.adk.tools import ToolContext
from .models import Input, Output
from .generator import TestGenerator

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
            Output: 処理結果の構造化データ（Output）。

        Raises:
            FileNotFoundError: 必要なアセットファイルが見つからない場合。
            Exception: その他の処理中に発生した例外。
        """
        skill = self.params.skill

        # 分離された TestGenerator クラスを利用してテストケースを自律生成 (DI用の無駄な引数を完全排除)
        generator = TestGenerator(skill_name=skill)
        eval_set_path = generator.generate_and_save()

        # 生成された評価セットファイルのパスをセッション状態に保存
        self.tool_context.state["eval_set_path"] = eval_set_path

        result_message = f"成功: 単体テストが {eval_set_path} に生成されました。"
        return Output(value=result_message)
