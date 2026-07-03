"""
Unified entry point for spec-writer.
"""
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommand, CommandLineRunner

# 同一ディレクトリのビジネスロジックモジュールをインポート可能にする
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spec_writer import process_message

if __name__ == "__main__":
    cmd = SkillCommand.from_argv("spec-writer", sys.argv[1:])
    runner = CommandLineRunner(cmd)
    runner.run(process_message)
