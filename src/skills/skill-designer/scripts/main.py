"""
Unified entry point for skill-designer.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommand, CommandLineRunner

from .skill_designer import process_message

if __name__ == "__main__":
    cmd = SkillCommand.from_argv("skill-designer", sys.argv[1:])
    runner = CommandLineRunner(cmd)
    runner.run(process_message)
