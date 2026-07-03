"""
Unified entry point for skill-manager.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommand, CommandLineRunner

from .manage_skills import manage_skills_logic, set_skill_tier

if __name__ == "__main__":
    cmd = SkillCommand.from_argv("skill-manager", sys.argv[1:])
    runner = CommandLineRunner(cmd)
    runner.run(manage_skills_logic)
