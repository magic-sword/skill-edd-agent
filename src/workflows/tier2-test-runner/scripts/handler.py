from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from .models import RunTier2TestOutput
from .executor import SkillExecutor
from .test_runner_client import TestRunnerClient
from .skill_state_client import SkillStateClient

def run_tier2_test(skill: str, tool_context: ToolContext = None) -> RunTier2TestOutput:
    """指定されたスキルに対して contract, golden, judge テストを実行し、すべて成功した場合はスキルをTier 2として登録します。

    Args:
        skill: 検証および昇格対象のスキル名。
        tool_context: ADKのToolContextインスタンス。

    Returns:
        実行結果オブジェクト (RunTier2TestOutput)。
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
    return executor.run_tier2_test(skill=skill)
