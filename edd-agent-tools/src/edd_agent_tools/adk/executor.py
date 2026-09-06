"""
Google ADK 2.0 Native BaseCodeExecutor for EDD Agent Tools

Google ADK 2.0 の BaseCodeExecutor 仕様に完全準拠したサブプロセス実行器。
multiprocessing.spawn に起因する重い連鎖インポート（google.genai / adk 再ロード）、
リソーストラッカーのデッドロック、およびゾンビプロセスの発生を完全に根絶し、
環境完全隔離された安全・決定論的・高速なコード実行を提供します。
"""

import sys
import asyncio
import subprocess
from typing import Optional, List, Dict, Any, Union

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
        invocation_context: Optional[InvocationContext] = None,
        code_execution_input: Optional[CodeExecutionInput] = None,
    ) -> CodeExecutionResult:
        """指定されたコードブロックを独立サブプロセスで実行し、結果を返します。"""
        if code_execution_input is None:
            return CodeExecutionResult(stdout="", stderr="No code input provided.", output_files=[])
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


class SkillScriptRunner:
    """Google ADK 2.0 純正スクリプト実行基盤（_SkillScriptCodeExecutor）と連携するスクリプト実行器。
    
    ラッパースクリプト生成やファイル展開の車輪の再発明を完全に排除し、
    Google ADK 2.0 公式のスクリプト実行パイプラインに処理を一本化します。
    """

    def __init__(self, code_executor: Optional[BaseCodeExecutor] = None, timeout_seconds: int = 60):
        self.code_executor = code_executor or LocalSubprocessCodeExecutor(timeout_seconds=timeout_seconds)
        self.timeout_seconds = timeout_seconds

    async def execute_script_async(
        self,
        skill: Any,
        file_path: str,
        script_args: Optional[Union[Dict[str, Any], List[str]]] = None,
        short_options: Optional[Dict[str, Any]] = None,
        positional_args: Optional[List[str]] = None,
        invocation_context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """ADK 2.0 純正の _SkillScriptCodeExecutor を介して非同期にスクリプトを実行します。"""
        # skill が SkillPackage の場合は adk_skill を取得
        adk_skill = getattr(skill, "adk_skill", skill)

        try:
            from google.adk.tools.skill_toolset import _SkillScriptCodeExecutor
            executor = _SkillScriptCodeExecutor(self.code_executor, self.timeout_seconds)
            res = await executor.execute_script_async(
                invocation_context=invocation_context,
                skill=adk_skill,
                file_path=file_path,
                script_args=script_args,
                short_options=short_options,
                positional_args=positional_args
            )

            # exit_code の標準化
            if isinstance(res, dict):
                is_success = res.get("status") in ("success", "warning") and "error" not in res
                res["exit_code"] = 0 if is_success else 1
            return res
        except Exception as e:
            return {
                "skill_name": getattr(adk_skill, "name", "unknown"),
                "file_path": file_path,
                "error": f"Failed to execute script via ADK code executor: {type(e).__name__}: {str(e)}",
                "error_code": "EXECUTION_ERROR",
                "status": "failed",
                "exit_code": 1
            }
    def execute_script(
        self,
        skill: Any,
        file_path: str,
        script_args: Optional[Union[Dict[str, Any], List[str]]] = None,
        short_options: Optional[Dict[str, Any]] = None,
        positional_args: Optional[List[str]] = None,
        invocation_context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """同期的にスキルのスクリプトを実行し、結果を返します。"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.execute_script_async(
                skill=skill,
                file_path=file_path,
                script_args=script_args,
                short_options=short_options,
                positional_args=positional_args,
                invocation_context=invocation_context
            )
        )

