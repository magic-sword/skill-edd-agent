import subprocess
from google.adk.tools import ToolContext

def run_system_command(tool_context: ToolContext) -> str:
    """
    指定されたシェルコマンドを同期的に実行し、標準出力と標準エラー出力を返します。
    システム側の 10秒 タイムアウト制限を受けず、完了するまで実行を待機します。
    """
    command = tool_context.state.get("command")
    if not command:
        return "Error: No command specified in 'state'."
        
    cwd = tool_context.state.get("cwd", "/workspace")
    timeout = tool_context.state.get("timeout_seconds", 120)  # デフォルト2分
    
    try:
        # 同期実行し、出力をキャプチャ
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout + result.stderr
        return f"Command exit code: {result.returncode}\n\nOutput:\n{output}"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"
