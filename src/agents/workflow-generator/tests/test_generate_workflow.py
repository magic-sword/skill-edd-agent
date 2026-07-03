import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import os
import shutil
import json
import asyncio
import sys

# テスト対象をインポートできるように sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import generate_workflow
from google.adk.tools import ToolContext
from edd_agent_tools.testing import MockInvocationContext

class TestGenerateWorkflow(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "tmp_test_output"))
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("generate_workflow.run_workflow_developer_agent")
    async def test_generate_workflow_code(self, mock_run_agent):
        # mock_run_agent が実行されたら、ファイルが作成されるように模擬する
        async def fake_run(output_dir, workflow_name, prompt, model, max_turns):
            os.makedirs(os.path.join(output_dir, "scripts"), exist_ok=True)
            with open(os.path.join(output_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write("# dummy skill md")
            with open(os.path.join(output_dir, "scripts", "workflow.py"), "w", encoding="utf-8") as f:
                f.write("# dummy workflow")
            with open(os.path.join(output_dir, "scripts", "main.py"), "w", encoding="utf-8") as f:
                f.write("# dummy runner")

        mock_run_agent.side_effect = fake_run

        tool_context = ToolContext(invocation_context=MockInvocationContext())
        tool_context.state.update({
            "workflow_name": "test-workflow",
            "prompt": "Test prompt description",
            "output_dir": self.test_dir
        })

        # 実行
        result = await generate_workflow.generate_workflow_code(tool_context)

        self.assertIn("Success", result)
        self.assertEqual(tool_context.state["workflow_dir"], self.test_dir)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "SKILL.md")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "scripts", "workflow.py")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "scripts", "main.py")))

if __name__ == "__main__":
    unittest.main()
