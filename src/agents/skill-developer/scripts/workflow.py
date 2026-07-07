"""
skill-developer の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階関数・エージェントノード接続。
"""
from google.adk import Workflow
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
import json
from .models import Input, Output

state = SkillsState()
state.load()

skill_designer_module = state.get_skill("skill-designer").load_module()
skill_coder_module = state.get_skill("skill-coder").load_module()
skill_spec_writer_module = state.get_skill("skill-spec-writer").load_module()

def run_design_skill_step(tool_context: ToolContext) -> str:
    # skill-designer の Input パラメータを構築
    params = skill_designer_module.Input(
        prompt=tool_context.state.get("prompt"),
        skill=tool_context.state.get("skill"),
        output_dir=tool_context.state.get("output_dir"),
        design_path=tool_context.state.get("design_path"),
    )
    res_str = skill_designer_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        # skill-designer の出力を tool_context.state に更新
        tool_context.state.update(res_data)
    except Exception:
        # JSONデコードエラーの場合でも、元の文字列をstateに格納して後続処理を試みる
        tool_context.state.update({"design_output_raw": res_str})
    return res_str

def run_code_skill_step(tool_context: ToolContext) -> str:
    # skill-coder の Input パラメータを tool_context.state から取得
    params = skill_coder_module.Input(
        skill=tool_context.state.get("skill"),
        output_dir=tool_context.state.get("output_dir"),
        design_path=tool_context.state.get("design_path"),
        source_code_dir=tool_context.state.get("source_code_dir"),
    )
    res_str = skill_coder_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        # skill-coder の出力を tool_context.state に更新
        tool_context.state.update(res_data)
    except Exception:
        tool_context.state.update({"code_output_raw": res_str})
    return res_str

def run_write_spec_step(tool_context: ToolContext) -> str:
    # skill-spec-writer の Input パラメータを tool_context.state から取得
    params = skill_spec_writer_module.Input(
        skill=tool_context.state.get("skill"),
        source_code_dir=tool_context.state.get("source_code_dir"),
        output_dir=tool_context.state.get("output_dir"),
    )
    res_str = skill_spec_writer_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        # skill-spec-writer の出力を tool_context.state に更新
        tool_context.state.update(res_data)
    except Exception:
        tool_context.state.update({"spec_output_raw": res_str})
    
    # 最終的な出力として、Outputモデルの形式で dict を構築
    final_output_dir = tool_context.state.get("output_dir")
    final_status = tool_context.state.get("status", "success") # デフォルトはsuccess
    final_message = tool_context.state.get("message", "スキル開発ワークフローが完了しました。")

    # Output モデルに準拠した dict を JSON 文字列として返す
    final_result_dict = Output(
        status=final_status,
        message=final_message,
        output_dir=final_output_dir or "./" # output_dir が設定されていなければカレントディレクトリ
    ).model_dump()
    return json.dumps(final_result_dict)

root_workflow = Workflow(
    name="skill_developer",
    edges=[
        ("START", run_design_skill_step),
        (run_design_skill_step, run_code_skill_step),
        (run_code_skill_step, run_write_spec_step)
    ]
)
