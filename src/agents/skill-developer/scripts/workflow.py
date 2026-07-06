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

skill_designer_module = state.get_skill("skill-designer").load_module()
skill_coder_module = state.get_skill("skill-coder").load_module()
skill_spec_writer_module = state.get_skill("skill-spec-writer").load_module()

def run_skill_designer_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    params = skill_designer_module.Input(
        prompt=tool_context.state.get("prompt"),
        skill_name=tool_context.state.get("skill"),
        existing_design_path=tool_context.state.get("design_path"),
        output_base_dir=tool_context.state.get("output_dir")
    )
    res_str = skill_designer_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        tool_context.state.update(res_data)
    except Exception:
        pass
    return res_str

def run_skill_coder_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    params = skill_coder_module.Input(
        design_file_path=tool_context.state.get("design_path"),
        skill_name=tool_context.state.get("skill_name"),
        existing_source_code_dir=tool_context.state.get("source_code_dir"),
        output_base_dir=tool_context.state.get("output_dir"),
        prompt=tool_context.state.get("prompt")
    )
    res_str = skill_coder_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        tool_context.state.update(res_data)
    except Exception:
        pass
    return res_str

def run_skill_spec_writer_step(tool_context: ToolContext) -> str:
    # セマンティックにマッピングされた引数の抽出
    params = skill_spec_writer_module.Input(
        design_file_path=tool_context.state.get("design_path"),
        source_code_directory_path=tool_context.state.get("source_code_dir"),
        skill_name=tool_context.state.get("skill_name"),
        output_base_dir=tool_context.state.get("output_dir"),
        prompt=tool_context.state.get("prompt")
    )
    res_str = skill_spec_writer_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        tool_context.state.update(res_data)
    except Exception:
        pass
    return res_str

root_workflow = Workflow(
    name="skill_developer",
    edges=[
        ("START", run_skill_designer_step),
        (run_skill_designer_step, run_skill_coder_step),
        (run_skill_coder_step, run_skill_spec_writer_step),
    ]
)