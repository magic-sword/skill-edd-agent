"""
Unified entry point for eval-unit-tester.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommandLineRunner

# 動的インポートとロードの解決
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_unit_tester import execute_unit_tester_logic, generate_unit_tests

if __name__ == "__main__":
    runner = SkillCommandLineRunner(description="Unit Test Case Generator")
    runner.add_argument("--skill_name", type=str, required=True)
    runner.run(execute_unit_tester_logic)
