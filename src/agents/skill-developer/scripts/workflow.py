"""
skill-developer の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階接続。
"""
from google.adk import Workflow

from .nodes.design_skill import run_design_skill_step
from .nodes.code_skill import run_code_skill_step
from .nodes.write_spec import run_write_spec_step

root_workflow = Workflow(
    name="skill_developer",
    edges=[
        ("START", run_design_skill_step),
        (run_design_skill_step, run_code_skill_step),
        (run_code_skill_step, run_write_spec_step),
    ]
)