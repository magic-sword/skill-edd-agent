"""
skill-developer の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階関数・エージェントノード接続。
"""
from google.adk import Workflow
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
import json
import os

state = SkillsState()
state.load()

skill_designer_module = state.get_skill("skill-designer").load_module()
skill_coder_module = state.get_skill("skill-coder").load_module()
skill_spec_writer_module = state.get_skill("skill-spec-writer").load_module()

def run_design_skill_step(tool_context: ToolContext) -> str:
    """
    skill-designer を実行し、スキル設計を生成します。
    """
    params = skill_designer_module.Input(
        prompt=tool_context.state.get("prompt"),
        skill=tool_context.state.get("skill"),
        output_dir=tool_context.state.get("output_dir"),
        design_path=tool_context.state.get("design_path")
    )
    res_str = skill_designer_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        # design_path と skill をセッション状態に保存
        if "design_path" in res_data:
            tool_context.state["design_path"] = res_data["design_path"]
        if "skill" in res_data:
            tool_context.state["skill"] = res_data["skill"]
        tool_context.state.update(res_data)
    except Exception:
        pass
    return res_str

def run_code_skill_step(tool_context: ToolContext) -> str:
    """
    skill-coder を実行し、スキルコードを生成します。
    """
    params = skill_coder_module.Input(
        design_path=tool_context.state.get("design_path"),
        skill=tool_context.state.get("skill"),
        output_dir=tool_context.state.get("output_dir"),
        source_code_dir=tool_context.state.get("source_code_dir")
    )
    res_str = skill_coder_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        # source_code_dir をセッション状態に保存
        if "source_code_dir" in res_data:
            tool_context.state["source_code_dir"] = res_data["source_code_dir"]
        tool_context.state.update(res_data)
    except Exception:
        pass
    return res_str

def run_write_spec_step(tool_context: ToolContext) -> str:
    """
    skill-spec-writer を実行し、スキル仕様書を生成します。
    """
    params = skill_spec_writer_module.Input(
        design_path=tool_context.state.get("design_path"),
        skill=tool_context.state.get("skill"),
        output_dir=tool_context.state.get("output_dir"),
        source_code_dir=tool_context.state.get("source_code_dir")
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
        ("START", run_design_skill_step),
        (run_design_skill_step, run_code_skill_step),
        (run_code_skill_step, run_write_spec_step),
    ]
)