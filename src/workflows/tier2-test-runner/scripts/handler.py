from edd_agent_tools import WorkflowRunner
from .models import Tier2TestRunnerOutput
from .workflow import root_workflow

class RuntimeInput:
    """内部引数コンパイル用ダミーオブジェクト。"""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def model_dump(self, **kwargs):
        return self.__dict__


def tier2_test_runner(skill_name: str, contract_eval_set_path: str, golden_eval_set_path: str, judge_eval_set_path: str, env: str) -> Tier2TestRunnerOutput:
    """指定されたスキルに対して依存関係検証、契約テスト、ゴールデンテスト、ジャッジテストを実行し、全て成功した場合にスキルをTier 2として登録するワークフロー。

    Args:
        skill_name: 評価対象スキルの名前。
        contract_eval_set_path: 契約テスト用のテストケースファイル (*.evalset.json) のパス。
        golden_eval_set_path: ゴールデンテスト用のテストケースファイル (*.evalset.json) のパス。
        judge_eval_set_path: ジャッジテスト用のテストケースファイル (*.evalset.json) のパス。
        env: テストを実行するサンドボックス環境（WorkspaceEnvProtocol）。

    Returns:
        実行結果オブジェクト (Tier2TestRunnerOutput)。
    """
    params = RuntimeInput(skill_name=skill_name, contract_eval_set_path=contract_eval_set_path, golden_eval_set_path=golden_eval_set_path, judge_eval_set_path=judge_eval_set_path, env=env)
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

