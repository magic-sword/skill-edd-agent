"""
Unified entry point for skill-developer.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommand, CommandLineRunner

# 動的インポートとロードの解決
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from develop_skill import develop_skill_logic

if __name__ == "__main__":
    cmd = SkillCommand.from_argv("skill-developer", sys.argv[1:])
    runner = CommandLineRunner(cmd)
    runner.run(develop_skill_logic)
