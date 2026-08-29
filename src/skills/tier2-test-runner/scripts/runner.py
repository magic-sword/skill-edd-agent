from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from edd_agent_tools.skills import SkillsState, SkillTier
from edd_agent_tools.evaluation import ContractTestRunner, SimulationEvalRunner
from edd_agent_tools.evaluation.sandbox import LocalWorkspaceEnv


class Tier2TestRunnerOutput(BaseModel):
    onboarding_status: str = Field(..., description="オンボーディングステータス ('success' または 'failed')")
    message: str = Field(..., description="詳細メッセージ")


def tier2_test_runner(
    skill_name: str,
    contract_eval_set_path: Optional[str] = None,
    golden_eval_set_path: Optional[str] = None,
    judge_eval_set_path: Optional[str] = None,
    env: Any = None
) -> Tier2TestRunnerOutput:
    """指定されたスキルに対して契約テスト、ゴールデンテスト、ジャッジテストを実行し、Tier 2として登録する。

    Args:
        skill_name: 評価対象スキルの名前。
        contract_eval_set_path: 契約テスト用ファイルのパス。
        golden_eval_set_path: ゴールデンテスト用ファイルのパス。
        judge_eval_set_path: ジャッジテスト用ファイルのパス。
        env: サンドボックス環境。

    Returns:
        Tier2TestRunnerOutput: 実行結果オブジェクト。
    """
    state = SkillsState()
    skill = state.get_skill(skill_name)
    if not skill:
        return Tier2TestRunnerOutput(
            onboarding_status="failed",
            message=f"対象スキル '{skill_name}' が見つかりませんでした。"
        )

    # 依存関係検証
    is_dag_valid, dag_errors = state.validate_dependency_graph()
    if not is_dag_valid:
        return Tier2TestRunnerOutput(
            onboarding_status="failed",
            message=f"依存関係検証に失敗しました: {dag_errors}"
        )

    if env is None or isinstance(env, str):
        env = LocalWorkspaceEnv()

    # 1. 契約テスト
    if contract_eval_set_path and Path(contract_eval_set_path).exists():
        import json
        with open(contract_eval_set_path, "r", encoding="utf-8") as f:
            cases_data = json.load(f)
        c_runner = ContractTestRunner()
        res = c_runner.run_tests(skill=skill, test_cases_data=cases_data, env=env)
        if res.failed > 0 or res.accuracy < 1.0:
            return Tier2TestRunnerOutput(
                onboarding_status="failed",
                message=f"契約テストに失敗しました (成功: {res.passed}/{res.total})"
            )

    # 2. ゴールデンテスト
    sim_runner = SimulationEvalRunner()
    if golden_eval_set_path and Path(golden_eval_set_path).exists():
        import json
        with open(golden_eval_set_path, "r", encoding="utf-8") as f:
            cases_data = json.load(f)
        res = sim_runner.run_tests(skill=skill, eval_set_data=cases_data, env=env)
        if res.accuracy < 0.9:
            return Tier2TestRunnerOutput(
                onboarding_status="failed",
                message=f"ゴールデンテストの精度が基準を満たしていません (精度: {res.accuracy:.2%})"
            )

    # 3. ジャッジテスト
    if judge_eval_set_path and Path(judge_eval_set_path).exists():
        import json
        with open(judge_eval_set_path, "r", encoding="utf-8") as f:
            cases_data = json.load(f)
        res = sim_runner.run_tests(skill=skill, eval_set_data=cases_data, env=env)
        if res.accuracy < 0.85:
            return Tier2TestRunnerOutput(
                onboarding_status="failed",
                message=f"LLMジャッジテストの精度が基準を満たしていません (精度: {res.accuracy:.2%})"
            )

    # Tier 2 昇格
    state.register_skill(skill_name=skill_name, tier=SkillTier.TIER2)

    return Tier2TestRunnerOutput(
        onboarding_status="success",
        message=f"スキル '{skill_name}' のTier 2評価テストがすべて合格し、登録を完了しました。"
    )
