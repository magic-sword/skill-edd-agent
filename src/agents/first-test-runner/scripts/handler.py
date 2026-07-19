from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from .models import RunFirstTestOutput
from .executor import SkillExecutor
from .test_runner_client import TestRunnerClient
from .skill_state_client import SkillStateClient

def run_first_test(skill: str, tool_context: ToolContext = None) -> RunFirstTestOutput:
    """指定されたスキルに対して一連のテストと検証を実行し、すべて成功した場合はスキルをTier 1として登録します。

    Args:
        skill: 試験対象のスキル名。
        tool_context: ADKのToolContextインスタンス。

    Returns:
        実行結果オブジェクト (RunFirstTestOutput)。
    """
    if tool_context is None:
        raise ValueError("Error: ToolContext が提供されていません。")

    skills_state = SkillsState()
    test_runner_client = TestRunnerClient(tool_context=tool_context)
    skill_state_client = SkillStateClient(skills_state=skills_state)

    executor = SkillExecutor(
        tool_context=tool_context,
        skills_state=skills_state,
        test_runner_client=test_runner_client,
        skill_state_client=skill_state_client
    )
    return executor.run_first_test(skill=skill)
