import os
import sys
from edd_agent_tools.testing import ADKEvalRunner
from edd_agent_tools.models import EvalRunResult

class TestRunner:
    def run_adk_eval(
        self,
        skill: str,
        eval_set_path: str,
        config_file_path: str,
        timeout_seconds: int,
        cwd: str = "/workspace"
    ) -> EvalRunResult:
        """
        adk eval コマンドをサブプロセスとして実行します。
        mock-executor専用として、常に環境変数 MOCK_TOOLS='load_skill' を設定します。
        """
        print(f"Running mock-executor for skill: {skill}")
        print(f"Eval set: {eval_set_path}")
        print(f"Threshold accuracy: (handled by logic.py), Timeout: {timeout_seconds}s")

        # adk evalの環境変数の設定
        env = {
            "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
            "SKILL": skill
        }
        
        # 評価対象としてモック専用エントリーポイントを指定
        result = ADKEvalRunner.run_eval(
            agent_dir="/workspace/src/mock_entry",
            eval_set_path=eval_set_path,
            config_file_path=config_file_path,
            timeout_seconds=timeout_seconds,
            env_vars=env,
            cwd=cwd
        )

        return result

