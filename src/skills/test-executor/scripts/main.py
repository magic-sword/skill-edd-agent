"""
Unified entry point for test-executor.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommand, CommandLineRunner

from .execute_test import execute_test_logic, run_skill_tests

if __name__ == "__main__":
    cmd = SkillCommand.from_argv("test-executor", sys.argv[1:])
    runner = CommandLineRunner(cmd)
    runner.run(execute_test_logic)
