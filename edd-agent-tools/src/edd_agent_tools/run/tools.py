import os
import fnmatch
from typing import Any
from google.adk.tools.environment._write_file_tool import WriteFileTool
from google.adk.tools.environment._edit_file_tool import EditFileTool
from google.adk.tools import ToolContext

def _is_restricted(path: str, patterns: list[str]) -> bool:
    basename = os.path.basename(path)
    for pattern in patterns:
        if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(path, pattern):
            return True
    return False

class SafeWriteFileTool(WriteFileTool):
    """
    指定されたファイル名パターンへの書き込みを禁止できる、安全な WriteFileTool。
    """
    def __init__(self, local_env, restricted_patterns: list[str]):
        super().__init__(local_env)
        self.restricted_patterns = restricted_patterns

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        path = args.get('path', '')
        if _is_restricted(path, self.restricted_patterns):
            return {
                'status': 'error',
                'error': (
                    f"Writing to '{path}' is strictly prohibited because it is a system-managed file. "
                    f"Do NOT attempt to overwrite this file. "
                    f"Write your custom logic in 'scripts/' directory instead."
                )
            }
        return await super().run_async(args=args, tool_context=tool_context)

class SafeEditFileTool(EditFileTool):
    """
    指定されたファイル名パターンへの編集を禁止できる、安全な EditFileTool。
    """
    def __init__(self, local_env, restricted_patterns: list[str]):
        super().__init__(local_env)
        self.restricted_patterns = restricted_patterns

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        path = args.get('path', '')
        if _is_restricted(path, self.restricted_patterns):
            return {
                'status': 'error',
                'error': (
                    f"Editing '{path}' is strictly prohibited because it is a system-managed file. "
                    f"Do NOT attempt to modify this file. "
                    f"Write your custom logic in 'scripts/' directory instead."
                )
            }
        return await super().run_async(args=args, tool_context=tool_context)

