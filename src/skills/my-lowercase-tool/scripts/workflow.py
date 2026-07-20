"""
skill-developer の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した関数ノード接続。
"""
from google.adk import Workflow
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
import json

state = SkillsState()
state.load()

developer_router_module = state.get_skill("developer-router").load_module()
skill_designer_module = state.get_skill("skill-designer").load_module()
workflow_designer_module = state.get_skill("workflow-designer").load_module()
skill_coder_module = state.get_skill("skill-coder").load_module()
skill_spec_writer_module = state.get_skill("skill-spec-writer").load_module()
test_generator_module = state.get_skill("test-generator").load_module()
design_validator_module = state.get_skill("design-validator").load_module()
import_validator_module = state.get_skill("import-validator").load_module()
test_executor_module = state.get_skill("test-executor").load_module()

def run_developer_router_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = developer_router_module.developer_router(
        prompt=tool_context.state.get('prompt')
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_skill_designer_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = skill_designer_module.skill_designer(
        prompt=tool_context.state.get('prompt'),
        summary=None,
        output_dir=tool_context.state.get('output_dir'),
        skill=tool_context.state.get('skill'),
        source_code_dir=tool_context.state.get('source_code_dir'),
        target_entry=tool_context.state.get('target_entry')
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_workflow_designer_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = workflow_designer_module.workflow_designer(
        prompt=tool_context.state.get('prompt'),
        summary=None,
        output_dir=tool_context.state.get('output_dir'),
        target_entry=tool_context.state.get('target_entry')
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_skill_coder_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = skill_coder_module.skill_coder(
        prompt=tool_context.state.get('prompt'),
        skill=tool_context.state.get('design-module.developed_skill_name'),
        design_path=os.path.join(tool_context.state.get('design-module.final_skill_output_dir'), 'design.json'),
        output_dir=tool_context.state.get('design-module.final_skill_output_dir')
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_skill_spec_writer_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = skill_spec_writer_module.generate_skill_spec(
        design_path=os.path.join(tool_context.state.get('design-module.final_skill_output_dir'), 'design.json'),
        skill=tool_context.state.get('design-module.developed_skill_name'),
        output_dir=tool_context.state.get('design-module.final_skill_output_dir'),
        source_code_dir=tool_context.state.get('source_code_dir'),
        prompt=tool_context.state.get('prompt')
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_test_generator_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = test_generator_module.generate_test_cases(
        skill=tool_context.state.get('design-module.developed_skill_name'),
        test_type=tool_context.state.get('test_type')
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_design_validator_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = design_validator_module.skill_developer(
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_import_validator_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = import_validator_module.validate_skill_import(
        skill=tool_context.state.get('design-module.developed_skill_name')
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

def run_test_executor_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    res = test_executor_module.execute_adk_simulation(
        skill=tool_context.state.get('design-module.developed_skill_name'),
        eval_set_path=tool_context.state.get('eval_set_path'),
        test_type=tool_context.state.get('test_type'),
        threshold_accuracy=tool_context.state.get('threshold_accuracy')
    )
    from edd_agent_tools import merge_result_to_state
    return merge_result_to_state(tool_context, res)

root_workflow = Workflow(
    name="skill_developer",
    edges=[
        ("START", run_developer_router_step),
        (run_developer_router_step, run_skill_designer_step),
        (run_skill_designer_step, run_workflow_designer_step),
        (run_workflow_designer_step, run_skill_coder_step),
        (run_skill_coder_step, run_skill_spec_writer_step),
        (run_skill_spec_writer_step, run_test_generator_step),
        (run_test_generator_step, run_design_validator_step),
        (run_design_validator_step, run_import_validator_step),
        (run_import_validator_step, run_test_executor_step),
    ]
)