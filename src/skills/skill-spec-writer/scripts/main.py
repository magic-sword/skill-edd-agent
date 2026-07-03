"""
Unified entry point for skill-spec-writer.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommand, CommandLineRunner

from .spec_writer import process_message

if __name__ == "__main__":
    cmd = SkillCommand.from_argv("skill-spec-writer", sys.argv[1:])
    runner = CommandLineRunner(cmd)
    runner.run(process_message)
