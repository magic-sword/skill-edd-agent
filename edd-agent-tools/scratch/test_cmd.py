import sys
import os

# パスの解決
sys.path.append("/workspace/edd-agent-tools/src")

from edd_agent_tools.utils import run_system_command
from google.adk.tools import ToolContext
from edd_agent_tools.testing import MockInvocationContext

# テスト 1: 同期的な echo 実行
print("--- Test 1: Simple echo ---")
context = ToolContext(invocation_context=MockInvocationContext())
context.state["command"] = "echo 'Success: Hello from run_system_command'"
context.state["cwd"] = "/workspace"
res = run_system_command(context)
print(res)

# テスト 2: タイムアウトの検証
print("\n--- Test 2: Timeout verification (sleep 5 with 2s timeout) ---")
context2 = ToolContext(invocation_context=MockInvocationContext())
context2.state["command"] = "sleep 5"
context2.state["cwd"] = "/workspace"
context2.state["timeout_seconds"] = 2
res2 = run_system_command(context2)
print(res2)
