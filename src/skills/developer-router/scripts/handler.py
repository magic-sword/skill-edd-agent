from .models import DeveloperRouterOutput
from .executor import DeveloperRouterExecutor

def developer_router(prompt: str) -> DeveloperRouterOutput:
    """ユーザーの要件プロンプトから、単体スキル（skill）かワークフロー（workflow）かを分類して判定します。

    Args:
        prompt: 開発したい機能の要件プロンプト。

    Returns:
        実行結果オブジェクト (DeveloperRouterOutput)。
    """
    executor = DeveloperRouterExecutor()
    return executor.route_requirement(prompt=prompt)
