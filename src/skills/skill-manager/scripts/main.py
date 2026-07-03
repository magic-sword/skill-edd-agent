"""
Unified entry point for skill-manager.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommandLineRunner

# 動的インポートとロードの解決
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manage_skills import manage_skills_logic, set_skill_tier

if __name__ == "__main__":
    runner = SkillCommandLineRunner(description="Skill Tier Registry Manager CLI")
    runner.add_argument("--command", choices=["register", "get-tier", "set-tier", "list", "update-meta"], required=True, help="Command to execute")
    runner.add_argument("--skill_name", help="Name of the skill")
    runner.add_argument("--tier", type=int, choices=[0, 1, 2, 3], help="Tier value (0, 1, 2, 3)")
    runner.add_argument("--registry_path", help="Path to skills_registry.json file")
    runner.run(manage_skills_logic)
