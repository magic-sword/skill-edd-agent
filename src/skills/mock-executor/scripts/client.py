import os
from edd_agent_tools import ADKEvalRunner, SkillRegistry, EvalRunResult, Skill

class ADKEvalClient:
    """
    ADK評価ツール（ADKEvalRunner, SkillRegistry）をラップするクライアントクラス。
    """
    def __init__(self):
        self._registry = SkillRegistry()

    def get_skill(self, skill_name_or_path: str) -> Skill:
        """指定されたスキル名またはパスからスキル情報を取得します。"""
        return self._registry.get_skill(name=skill_name_or_path)

    def resolve_and_prepare_eval_config(self, target_skill: Skill, eval_set_path: str) -> str:
        """
        評価設定ファイルのパスを解決し、存在しない場合はデフォルト設定を生成します。
        """
        config_file_path = target_skill.resolve_eval_config_path(eval_set_path)
        if not os.path.exists(config_file_path):
            test_type = "trigger" if "trigger" in eval_set_path else "unit"
            # executor_old.py のデフォルト設定を踏襲
            target_skill.save_eval_config({"criteria": {"response_match_score": 0.8}}, test_type)
            print(f"Generated default eval config file: {config_file_path}")
        return config_file_path

    def run_eval(
        self,
        agent_dir: str,
        eval_set_path: str,
        config_file_path: str,
        timeout_seconds: int,
        env_vars: dict,
    ) -> EvalRunResult:
        """
        ADK評価シミュレーションを実行します。
        """
        print(f"Running ADK eval with:")
        print(f"  Agent directory: {agent_dir}")
        print(f"  Eval set path: {eval_set_path}")
        print(f"  Config file path: {config_file_path}")
        print(f"  Timeout: {timeout_seconds}s")
        return ADKEvalRunner.run_eval(
            agent_dir=agent_dir,
            eval_set_path=eval_set_path,
            config_file_path=config_file_path,
            timeout_seconds=timeout_seconds,
            env_vars=env_vars
        )
