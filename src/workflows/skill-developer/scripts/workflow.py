"""
skill-developer の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階接続。
"""
from google.adk import Workflow

from .nodes.route_requirement import run_route_requirement_step
from .nodes.design_skill import run_design_skill_step
from .nodes.design_workflow import run_design_workflow_step
from .nodes.code_skill import run_code_skill_step
from .nodes.write_spec import run_write_spec_step
from .nodes.finalize_assets import run_finalize_assets_step

root_workflow = Workflow(
    name="skill_developer",
    edges=[
        ("START", run_route_requirement_step),
        (run_route_requirement_step, {
            "skill": run_design_skill_step,
            "workflow": run_design_workflow_step
        }),
        (run_design_skill_step, run_code_skill_step),
        (run_design_workflow_step, run_code_skill_step),
        (run_code_skill_step, run_write_spec_step),
        (run_write_spec_step, run_finalize_assets_step),
    ]
)