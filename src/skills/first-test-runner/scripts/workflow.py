"""
tier1-skill-onboarding の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階接続。
"""
from google.adk import Workflow

from .nodes.validate_dependencies import run_validate_dependencies_step
from .nodes.run_trigger_test import run_run_trigger_test_step
from .nodes.run_contract_test import run_run_contract_test_step
from .nodes.register_tier1 import run_register_tier1_step

root_workflow = Workflow(
    name="tier1_skill_onboarding",
    edges=[
        ("START", run_validate_dependencies_step),
        (run_validate_dependencies_step, run_run_trigger_test_step),
        (run_run_trigger_test_step, run_run_contract_test_step),
        (run_run_contract_test_step, run_register_tier1_step),
    ]
)