"""
Unified entry point for eval-unit-tester.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommand, CommandLineRunner

from .eval_unit_tester import execute_unit_tester_logic, generate_unit_tests

if __name__ == "__main__":
    cmd = SkillCommand.from_argv("eval-unit-tester", sys.argv[1:])
    runner = CommandLineRunner(cmd)
    runner.run(execute_unit_tester_logic)
