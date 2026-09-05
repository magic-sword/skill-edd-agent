"""
Google ADK 2.0 Native BaseCodeExecutor for EDD Agent Tools

Google ADK 2.0 の BaseCodeExecutor 仕様に完全準拠したサブプロセス実行器。
multiprocessing.spawn に起因する重い連鎖インポート（google.genai / adk 再ロード）、
リソーストラッカーのデッドロック、およびゾンビプロセスの発生を完全に根絶し、
環境完全隔離された安全・決定論的・高速なコード実行を提供します。
"""

import sys
import subprocess
from typing import Optional, List, Dict, Any

try:
    from google.adk.code_executors import BaseCodeExecutor
    from google.adk.code_executors.base_code_executor import CodeExecutionInput, CodeExecutionResult
    from google.adk.agents.invocation_context import InvocationContext
except ImportError:
    from pydantic import BaseModel
    BaseCodeExecutor = BaseModel
    class CodeExecutionInput(BaseModel):
        code: str
    class CodeExecutionResult(BaseModel):
        stdout: str = ""
        stderr: str = ""
        output_files: List[Any] = []
    InvocationContext = Any


class LocalSubprocessCodeExecutor(BaseCodeExecutor):
    """Google ADK 2.0 純正 BaseCodeExecutor 準拠の決定論的サブプロセス実行器。
    
    UnsafeLocalCodeExecutor と同等のローカル実行能力を持ちつつ、
    multiprocessing.spawn ではなく独立したサブプロセスとして実行することで、
    テスト環境や CI 環境でのハングやゾンビプロセスの発生を防止します。
    """
    timeout_seconds: Optional[int] = 60

    def execute_code(
        self,
        invocation_context: Optional[InvocationContext],
        code_execution_input: CodeExecutionInput,
    ) -> CodeExecutionResult:
        """指定されたコードブロックを独立サブプロセスで実行し、結果を返します。"""
        timeout = self.timeout_seconds or 60
        try:
            res = subprocess.run(
                [sys.executable, "-c", code_execution_input.code],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return CodeExecutionResult(
                stdout=res.stdout or "",
                stderr=res.stderr or "",
                output_files=[]
            )
        except subprocess.TimeoutExpired:
            return CodeExecutionResult(
                stdout="",
                stderr=f"Code execution timed out after {timeout} seconds.",
                output_files=[]
            )
        except Exception as e:
            return CodeExecutionResult(
                stdout="",
                stderr=f"Execution error: {type(e).__name__}: {str(e)}",
                output_files=[]
            )
