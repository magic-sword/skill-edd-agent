"""
skill-developer の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階関数・エージェントノード接続。
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

def run_design_skill_step(tool_context: ToolContext) -> str:
    """
    skill-designerスキルを実行するステップ。
    tool_context.stateから必要な入力パラメータを取得し、skill-designerに渡します。
    """
    # skill-developerの入力からpromptとoutput_dir, skillを取得
    prompt = tool_context.state.get("prompt")
    output_dir = tool_context.state.get("output_dir")
    skill = tool_context.state.get("skill")

    # skill-designerのInputオブジェクトを生成
    params = skill_designer_module.Input(
        prompt=prompt,
        output_dir=output_dir,
        skill=skill
    )
    res_str = skill_designer_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        # skill-designerの出力（例: design_path, skill, output_dir）をstateに更新
        tool_context.state.update(res_data)
    except Exception:
        pass
    return res_str

def run_code_skill_step(tool_context: ToolContext) -> str:
    """
    skill-coderスキルを実行するステップ。
    tool_context.stateから必要な入力パラメータを取得し、skill-coderに渡します。
    """
    # skill-designerの出力からdesign_pathを取得
    design_path = tool_context.state.get("design_path")
    # skill-developerの入力からoutput_dir, skillを取得
    output_dir = tool_context.state.get("output_dir")
    skill = tool_context.state.get("skill")

    # skill-coderのInputオブジェクトを生成
    params = skill_coder_module.Input(
        design_path=design_path,
        output_dir=output_dir,
        skill=skill
    )
    res_str = skill_coder_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        # skill-coderの出力（例: source_code_dir, skill, output_dir）をstateに更新
        tool_context.state.update(res_data)
    except Exception:
        pass
    return res_str

def run_write_spec_step(tool_context: ToolContext) -> str:
    """
    skill-spec-writerスキルを実行するステップ。
    tool_context.stateから必要な入力パラメータを取得し、skill-spec-writerに渡します。
    """
    # skill-coderの出力からsource_code_dirを取得
    source_code_dir = tool_context.state.get("source_code_dir")
    # skill-developerの入力からoutput_dir, skillを取得
    output_dir = tool_context.state.get("output_dir")
    skill = tool_context.state.get("skill")

    # skill-spec-writerのInputオブジェクトを生成
    params = skill_spec_writer_module.Input(
        source_code_dir=source_code_dir,
        output_dir=output_dir,
        skill=skill
    )
    res_str = skill_spec_writer_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        # skill-spec-writerの出力（例: output_dir, skill）をstateに更新
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