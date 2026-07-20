from edd_agent_tools import WorkflowRunner
from .models import Tier2TestRunnerOutput
from .workflow import root_workflow

class RuntimeInput:
    """内部引数コンパイル用ダミーオブジェクト。"""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def model_dump(self, **kwargs):
        return self.__dict__


def tier2_test_runner(skill: str) -> Tier2TestRunnerOutput:
    """指定されたスキルに対して contract, golden, judge テストを実行し、すべて成功した場合はスキルをTier 2として登録するワークフロー。

    Args:
        skill: 検証および昇格対象のスキル名。

    Returns:
        実行結果オブジェクト (Tier2TestRunnerOutput)。
    """
    params = RuntimeInput(skill=skill)
    runner = WorkflowRunner(
        workflow_name="tier2-test-runner",
        root_workflow=root_workflow
    )
    result_dict = runner.run(params)
    
    output_data = {}
    for field in Tier2TestRunnerOutput.model_fields.keys():
        if field in result_dict:
            output_data[field] = result_dict[field]
        elif "state" in result_dict and field in result_dict["state"]:
            output_data[field] = result_dict["state"][field]
            
    if not output_data and "value" in Tier2TestRunnerOutput.model_fields:
        output_data["value"] = result_dict.get("message", "success")
        
    return Tier2TestRunnerOutput(**output_data)

