"""
tier3-test-runner の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階接続。
"""
from google.adk import Workflow

from .nodes.validate_dependencies import validate_dependencies
from .nodes.run_contract_test import run_contract_test
from .nodes.run_golden_test import run_golden_test
from .nodes.run_judge_test import run_judge_test
from .nodes.run_adversarial_test import run_adversarial_test
from .nodes.register_tier3 import register_tier3

root_workflow = Workflow(
    name="tier3_test_runner",
    edges=[
        ("START", validate_dependencies),
        (validate_dependencies, run_contract_test),
        (run_contract_test, run_golden_test),
        (run_golden_test, run_judge_test),
        (run_judge_test, run_adversarial_test),
        (run_adversarial_test, register_tier3),
    ]
)
