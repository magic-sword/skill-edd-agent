"""
first-test-runner の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階接続。
"""
from google.adk import Workflow

from .nodes.run_trigger_evaluator import run_run_trigger_evaluator_step
from .nodes.run_test_executor import run_run_test_executor_step
from .nodes.run_import_validator import run_run_import_validator_step
from .nodes.run_design_validator import run_run_design_validator_step
from .nodes.evaluate_and_register_skill import run_evaluate_and_register_skill_step

root_workflow = Workflow(
    name="first_test_runner",
    edges=[
        ("START", run_run_trigger_evaluator_step),
        (run_run_trigger_evaluator_step, run_run_test_executor_step),
        (run_run_test_executor_step, run_run_import_validator_step),
        (run_run_import_validator_step, run_run_design_validator_step),
        (run_run_design_validator_step, run_evaluate_and_register_skill_step),
    ]
)