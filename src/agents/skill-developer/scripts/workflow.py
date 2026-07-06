"""
skill-developer の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階関数・エージェントノード接続。
"""
from google.adk import Workflow
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
import json
from typing import Dict, Any

state = SkillsState()
state.load()

skill_designer_module = state.get_skill("skill-designer").load_module()
skill_coder_module = state.get_skill("skill-coder").load_module()
skill_spec_writer_module = state.get_skill("skill-spec-writer").load_module()

def _update_state_from_json_response(tool_context: ToolContext, res_str: str) -> None:
    """JSON文字列のレスポンスを解析し、tool_context.stateを更新します。
    パースに失敗しても例外を発生させず、処理を引き継ぎます。
    """
    try:
        res_data = json.loads(res_str)
        if isinstance(res_data, dict):
            tool_context.state.update(res_data)
    except Exception:
        # JSONパースエラーが発生しても、処理を続行
        pass

def run_design_skill_step(tool_context: ToolContext) -> str:
    """
    skill-designer スキルを実行し、設計情報を生成します。
    """
    # tool_context.state から初期入力パラメータを取得
    params_dict: Dict[str, Any] = {
        "prompt": tool_context.state.get("prompt"),
        "skill": tool_context.state.get("skill"),
        "output_dir": tool_context.state.get("output_dir"),
    }
    # None の値を除外して、スキルに渡すパラメータを構築
    filtered_params = {k: v for k, v in params_dict.items() if v is not None}
    params = skill_designer_module.Input(**filtered_params)

    res_str = skill_designer_module.process_message(params, tool_context)
    _update_state_from_json_response(tool_context, res_str)
    return res_str

def run_code_skill_step(tool_context: ToolContext) -> str:
    """
    skill-coder スキルを実行し、ソースコードを生成します。
    """
    # tool_context.state から必要な入力パラメータを取得
    params_dict: Dict[str, Any] = {
        "design_path": tool_context.state.get("design_path"),
        "skill": tool_context.state.get("skill"),
        "output_dir": tool_context.state.get("output_dir"),
    }
    # None の値を除外して、スキルに渡すパラメータを構築
    filtered_params = {k: v for k, v in params_dict.items() if v is not None}
    params = skill_coder_module.Input(**filtered_params)

    res_str = skill_coder_module.process_message(params, tool_context)
    _update_state_from_json_response(tool_context, res_str)
    return res_str

def run_write_spec_step(tool_context: ToolContext) -> str:
    """
    skill-spec-writer スキルを実行し、仕様書を生成します。
    """
    # tool_context.state から必要な入力パラメータを取得
    params_dict: Dict[str, Any] = {
        "design_path": tool_context.state.get("design_path"),
        "source_code_dir": tool_context.state.get("source_code_dir"),
        "skill": tool_context.state.get("skill"),
        "output_dir": tool_context.state.get("output_dir"),
    }
    # None の値を除外して、スキルに渡すパラメータを構築
    filtered_params = {k: v for k, v in params_dict.items() if v is not None}
    params = skill_spec_writer_module.Input(**filtered_params)

    res_str = skill_spec_writer_module.process_message(params, tool_context)
    _update_state_from_json_response(tool_context, res_str)
    return res_str

root_workflow = Workflow(
    name="skill_developer",
    edges=[
        ("START", run_design_skill_step),
        (run_design_skill_step, run_code_skill_step),
        (run_code_skill_step, run_write_spec_step),
    ]
)