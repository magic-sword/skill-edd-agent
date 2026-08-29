from typing import Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field
from edd_agent_tools.skills import SkillsState, SkillTier
from edd_agent_tools.evaluation import ContractTestRunner, SimulationEvalRunner
from edd_agent_tools.evaluation.sandbox import LocalWorkspaceEnv


class Tier1SkillOnboardingOutput(BaseModel):
    onboarding_status: str = Field(..., description="オンボーディングステータス ('success' または 'failed')")
    message: str = Field(..., description="詳細メッセージ")


def tier1_skill_onboarding(skill_name: str, eval_set_base_path: str = "tests") -> Tier1SkillOnboardingOutput:
    """指定されたスキルの依存関係、トリガーテスト、契約テストを実行し、合格時にTier 1として登録する。

    Args:
        skill_name: Tier 1としてオンボーディングするスキル名。
        eval_set_base_path: 評価用テストケースファイルが格納されているベースディレクトリのパス。

    Returns:
        Tier1SkillOnboardingOutput: 実行結果オブジェクト。
    """
    state = SkillsState()
    skill = state.get_skill(skill_name)
    if not skill:
        return Tier1SkillOnboardingOutput(
            onboarding_status="failed",
            message=f"対象スキル '{skill_name}' が見つかりませんでした。"
        )

    # 1. 依存関係の検証
    is_dag_valid, dag_errors = state.validate_dependency_graph()
    if not is_dag_valid:
        return Tier1SkillOnboardingOutput(
            onboarding_status="failed",
            message=f"依存関係検証に失敗しました: {dag_errors}"
        )

    base_path = Path(eval_set_base_path)
    env = LocalWorkspaceEnv()

    # 2. 契約テストの実行
    contract_file = base_path / skill_name / f"{skill_name}_contract.evalset.json"
    if not contract_file.exists():
        contract_file = base_path / f"{skill_name}_contract.evalset.json"

    if contract_file.exists():
        contract_runner = ContractTestRunner()
        import json
        with open(contract_file, "r", encoding="utf-8") as f:
            cases_data = json.load(f)
        res = contract_runner.run_tests(skill=skill, test_cases_data=cases_data, env=env)
        if res.failed > 0 or res.accuracy < 1.0:
            return Tier1SkillOnboardingOutput(
                onboarding_status="failed",
                message=f"契約テストに失敗しました (成功: {res.passed}/{res.total})"
            )

    # 3. トリガーテストの実行
    trigger_file = base_path / skill_name / f"{skill_name}_trigger.evalset.json"
    if not trigger_file.exists():
        trigger_file = base_path / f"{skill_name}_trigger.evalset.json"

    if trigger_file.exists():
        sim_runner = SimulationEvalRunner()
        import json
        with open(trigger_file, "r", encoding="utf-8") as f:
            cases_data = json.load(f)
        res = sim_runner.run_tests(skill=skill, eval_set_data=cases_data, env=env)
        if res.accuracy < 0.9:
            return Tier1SkillOnboardingOutput(
                onboarding_status="failed",
                message=f"トリガーテストの精度が基準を満たしていません (精度: {res.accuracy:.2%}, 閾値: 90%)"
            )

    # 4. Tier 1 昇格
    state.register_skill(skill_name=skill_name, tier=SkillTier.TIER1)

    return Tier1SkillOnboardingOutput(
        onboarding_status="success",
        message=f"スキル '{skill_name}' のTier 1オンボーディングテストがすべて合格し、登録を完了しました。"
    )
