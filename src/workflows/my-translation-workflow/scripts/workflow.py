"""
tier2-test-runner の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した関数ノード接続。
"""
from google.adk import Workflow
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
import json

state = SkillsState()
state.load()

import_validator_module = state.get_skill("import-validator").load_module()
golden_test_generator_module = state.get_skill("golden-test-generator").load_module()
golden_test_executor_module = state.get_skill("golden-test-executor").load_module()
judge_test_generator_module = state.get_skill("judge-test-generator").load_module()
judge_test_executor_module = state.get_skill("judge-test-executor").load_module()

def run_import_validator_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = import_validator_module.validate_skill_import(
        skill=tool_context.state.get('skill')
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_golden_test_generator_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = golden_test_generator_module.generate_tests(
        skill_name=tool_context.state.get('skill'),
        output_path=f"/tmp/{tool_context.state.get('skill')}_golden.evalset.json"
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_golden_test_executor_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = golden_test_executor_module.run_tests(
        skill_name=tool_context.state.get('skill'),
        eval_set_path=f"/tmp/{tool_context.state.get('skill')}_golden.evalset.json",
        env="LocalWorkspaceEnv"
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_judge_test_generator_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = judge_test_generator_module.generate_tests(
        skill_name=tool_context.state.get('skill'),
        output_path=f"/tmp/{tool_context.state.get('skill')}_judge.evalset.json"
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_judge_test_executor_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = judge_test_executor_module.run_tests(
        skill_name=tool_context.state.get('skill'),
        eval_set_path=f"/tmp/{tool_context.state.get('skill')}_judge.evalset.json",
        env="LocalWorkspaceEnv"
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

root_workflow = Workflow(
    name="tier2_test_runner",
    edges=[
        ("START", run_import_validator_step),
        (run_import_validator_step, run_golden_test_generator_step),
        (run_golden_test_generator_step, run_golden_test_executor_step),
        (run_golden_test_executor_step, run_judge_test_generator_step),
        (run_judge_test_generator_step, run_judge_test_executor_step),
    ]
)