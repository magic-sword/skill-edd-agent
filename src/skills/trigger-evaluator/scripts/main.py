"""
Unified entry point for trigger-evaluator.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommand, CommandLineRunner

from .evaluate_trigger import execute_trigger_logic, generate_trigger_tests

if __name__ == "__main__":
    cmd = SkillCommand.from_argv("trigger-evaluator", sys.argv[1:])
    runner = CommandLineRunner(cmd)
    runner.run(execute_trigger_logic)
