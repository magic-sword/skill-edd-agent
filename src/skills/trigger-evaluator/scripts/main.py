"""
Unified entry point for trigger-evaluator.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommandLineRunner

# 動的インポートとロードの解決
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate_trigger import execute_trigger_logic, generate_trigger_tests

if __name__ == "__main__":
    runner = SkillCommandLineRunner(description="指定されたスキルのトリガー定義の品質チェックとテスト生成を行います。")
    runner.add_argument("--skill_name", help="評価対象のスキル名")
    runner.run(execute_trigger_logic)
