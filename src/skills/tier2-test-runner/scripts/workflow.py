from google.adk import Workflow

from .nodes.validate_dependencies import validate_dependencies
from .nodes.run_contract_test import run_contract_test
from .nodes.run_golden_test import run_golden_test
from .nodes.run_judge_test import run_judge_test
from .nodes.register_tier2 import register_tier2

root_workflow = Workflow(
    name="tier2_test_runner",
    edges=[
        ("START", validate_dependencies),
        (validate_dependencies, run_contract_test),
        (run_contract_test, run_golden_test),
        (run_golden_test, run_judge_test),
        (run_judge_test, register_tier2),
    ]
)
