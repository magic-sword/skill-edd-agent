"""
skill-developer の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階接続。
"""
from google.adk import Workflow

from .nodes.route_requirement import run_route_requirement_step
from .nodes.design_skill import run_create_skill_step, run_update_skill_step
from .nodes.design_workflow import run_create_workflow_step, run_update_workflow_step
from .nodes.handle_proposal import run_handle_proposal_step
from .nodes.code_skill import run_code_skill_step
from .nodes.write_spec import run_write_spec_step
from .nodes.finalize_assets import run_finalize_assets_step

root_workflow = Workflow(
    name="skill_developer",
    edges=[
        ("START", run_route_requirement_step),
        (run_route_requirement_step, {
            "create_skill": run_create_skill_step,
            "update_skill": run_update_skill_step,
            "create_workflow": run_create_workflow_step,
            "update_workflow": run_update_workflow_step,
            "proposal": run_handle_proposal_step
        }),
        (run_create_skill_step, run_code_skill_step),
        (run_update_skill_step, run_code_skill_step),
        (run_create_workflow_step, run_code_skill_step),
        (run_update_workflow_step, run_code_skill_step),
        (run_code_skill_step, run_write_spec_step),
        (run_write_spec_step, run_finalize_assets_step),
    ]
)