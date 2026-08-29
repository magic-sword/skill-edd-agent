from edd_agent_tools import WorkflowRunner
from .models import Tier1SkillOnboardingOutput
from .workflow import root_workflow

class RuntimeInput:
    """内部引数コンパイル用ダミーオブジェクト。"""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def model_dump(self, **kwargs):
        return self.__dict__


def tier1_skill_onboarding(skill_name: str, eval_set_base_path: str) -> Tier1SkillOnboardingOutput:
    """試験対象のスキル名と評価セットのパスを受け取り、依存関係の検証、トリガーテスト、契約テストを実行し、すべてに合格した場合にスキルをTier 1として登録するワークフロー。

    Args:
        skill_name: Tier 1としてオンボーディングするスキルの名前。
        eval_set_base_path: 評価用のテストケースファイルが格納されているベースディレクトリのパス。

    Returns:
        実行結果オブジェクト (Tier1SkillOnboardingOutput)。
    """
    params = RuntimeInput(skill_name=skill_name, eval_set_base_path=eval_set_base_path)
    runner = WorkflowRunner(
        workflow_name="tier1-skill-onboarding",
        root_workflow=root_workflow
    )
    result_dict = runner.run(params)
    
    output_data = {}
    for field in Tier1SkillOnboardingOutput.model_fields.keys():
        if field in result_dict:
            output_data[field] = result_dict[field]
        elif "state" in result_dict and field in result_dict["state"]:
            output_data[field] = result_dict["state"][field]
            
    if not output_data and "value" in Tier1SkillOnboardingOutput.model_fields:
        output_data["value"] = result_dict.get("message", "success")
        
    return Tier1SkillOnboardingOutput(**output_data)

