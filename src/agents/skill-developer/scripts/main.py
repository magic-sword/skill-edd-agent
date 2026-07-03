"""
Unified entry point for skill-developer.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommandLineRunner

# 動的インポートとロードの解決
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from develop_skill import develop_skill_logic

if __name__ == "__main__":
    runner = SkillCommandLineRunner(description="Skill Developer Workflow Agent CLI")
    runner.add_argument("--skill_name", required=True, help="Name of the skill to develop")
    runner.add_argument("--prompt", required=True, help="Requirements prompt for the skill")
    runner.run(develop_skill_logic)
