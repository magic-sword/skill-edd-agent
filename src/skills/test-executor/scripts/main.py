"""
Unified entry point for test-executor.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommandLineRunner

# 動的インポートとロードの解決
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from execute_test import execute_test_logic, run_skill_tests

if __name__ == "__main__":
    runner = SkillCommandLineRunner(description="ADK evalテストを実行し、合格閾値に基づいて判定を行います。")
    runner.add_argument("--skill_name", type=str, help="テスト対象のスキル名")
    runner.add_argument("--eval_set_path", type=str, help="テストケース定義ファイルのパス")
    runner.add_argument("--threshold_accuracy", type=float, default=1.0, help="合格に必要な精度の閾値（0.0〜1.0）")
    runner.add_argument("--timeout_seconds", type=int, default=180, help="テスト実行のタイムアウト制限（秒）")
    runner.add_argument("--eval_mode", type=int, choices=[0, 1], default=1, help="ADK_EVAL_MODE の値 (1: 単体評価用, 0: 通常/トリガー評価用)")
    runner.run(execute_test_logic)
