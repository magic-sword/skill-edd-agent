"""
first-test-runner の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階関数・エージェントノード接続。
"""
from google.adk import Workflow
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState

"""
first-test-runner の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階関数・エージェントノード接続。
"""
from google.adk import Workflow
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
import json

# SkillsStateはスキルロードのために各ステップ関数内でインスタンス化する
# state = SkillsState()
# state.load() # ロードも各スキル呼び出し前に個別に行う

# スキルモジュールは各ステップ関数内でSkillsStateから取得する
# trigger_evaluator_module = state.get_skill("trigger-evaluator").load_module()
# test_executor_module = state.get_skill("test-executor").load_module()
# import_validator_module = state.get_skill("import-validator").load_module()
# design_validator_module = state.get_skill("design-validator").load_module()
from .nodes.evaluate_and_register_skill import run_evaluate_and_register_skill_step

def run_run_trigger_evaluator_step(tool_context: ToolContext) -> str:
    """
    trigger-evaluator スキルを実行し、結果を tool_context.state に保存します。
    """
    skills_state = SkillsState()
    skills_state.load()
    trigger_evaluator_module = skills_state.get_skill("trigger-evaluator").load_module()

    skill_name = tool_context.get_parameter("skill")
    params = trigger_evaluator_module.Input(skill=skill_name)
    res_str = trigger_evaluator_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        tool_context.state["trigger_evaluator_result"] = res_data
    except json.JSONDecodeError:
        tool_context.state["trigger_evaluator_result"] = {"status": "failed", "message": res_str}
    return res_str

def run_run_test_executor_step(tool_context: ToolContext) -> str:
    """
    test-executor スキルを実行し、結果を tool_context.state に保存します。
    """
    skills_state = SkillsState()
    skills_state.load()
    test_executor_module = skills_state.get_skill("test-executor").load_module()

    skill_name = tool_context.get_parameter("skill")
    threshold_accuracy = tool_context.get_parameter("threshold_accuracy", 1.0) # デフォルト値も取得
    params = test_executor_module.Input(skill=skill_name, threshold_accuracy=threshold_accuracy)
    res_str = test_executor_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        tool_context.state["test_executor_result"] = res_data
    except json.JSONDecodeError:
        tool_context.state["test_executor_result"] = {"status": "failed", "message": res_str}
    return res_str

def run_run_import_validator_step(tool_context: ToolContext) -> str:
    """
    import-validator スキルを実行し、結果を tool_context.state に保存します。
    """
    skills_state = SkillsState()
    skills_state.load()
    import_validator_module = skills_state.get_skill("import-validator").load_module()

    skill_name = tool_context.get_parameter("skill")
    params = import_validator_module.Input(skill=skill_name)
    res_str = import_validator_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        tool_context.state["import_validator_result"] = res_data
    except json.JSONDecodeError:
        tool_context.state["import_validator_result"] = {"status": "failed", "message": res_str}
    return res_str

def run_run_design_validator_step(tool_context: ToolContext) -> str:
    """
    design-validator スキルを実行し、結果を tool_context.state に保存します。
    """
    skills_state = SkillsState()
    skills_state.load()
    design_validator_module = skills_state.get_skill("design-validator").load_module()

    skill_name = tool_context.get_parameter("skill")
    params = design_validator_module.Input(skill=skill_name)
    res_str = design_validator_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        tool_context.state["design_validator_result"] = res_data
    except json.JSONDecodeError:
        tool_context.state["design_validator_result"] = {"status": "failed", "message": res_str}
    return res_str

root_workflow = Workflow(
    name="first_test_runner",
    edges=[
        ("START", run_run_trigger_evaluator_step),
        (run_run_trigger_evaluator_step, run_run_test_executor_step),
        (run_run_test_executor_step, run_run_import_validator_step),
        (run_run_import_validator_step, run_run_design_validator_step),
        (run_run_design_validator_step, run_evaluate_and_register_skill_step),
    ]
)