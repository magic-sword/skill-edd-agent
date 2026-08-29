from edd_agent_tools import WorkflowRunner
from .models import Tier3TestRunnerOutput
from .workflow import root_workflow

class RuntimeInput:
    """内部引数コンパイル用ダミーオブジェクト。"""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def model_dump(self, **kwargs):
        return self.__dict__


def tier3_test_runner(skill_name: str, contract_eval_set_path: str, golden_eval_set_path: str, judge_eval_set_path: str, adversarial_eval_set_path: str, env: str) -> Tier3TestRunnerOutput:
    """指定されたスキルに対して依存関係検証、契約テスト、ゴールデンテスト、ジャッジテスト、敵対的・限界テストを実行し、全て成功した場合にスキルをTier 3として登録するワークフロー。

    Args:
        skill_name: 評価対象スキルの名前。
        contract_eval_set_path: 契約テスト用のテストケースファイル (*.evalset.json) のパス。
        golden_eval_set_path: ゴールデンテスト用のテストケースファイル (*.evalset.json) のパス。
        judge_eval_set_path: ジャッジテスト用のテストケースファイル (*.evalset.json) のパス。
        adversarial_eval_set_path: 敵対的・限界テスト用のテストケースファイル (*.evalset.json) のパス。
        env: テストを実行するサンドボックス環境（WorkspaceEnvProtocol）。

    Returns:
        実行結果オブジェクト (Tier3TestRunnerOutput)。
    """
    params = RuntimeInput(skill_name=skill_name, contract_eval_set_path=contract_eval_set_path, golden_eval_set_path=golden_eval_set_path, judge_eval_set_path=judge_eval_set_path, adversarial_eval_set_path=adversarial_eval_set_path, env=env)
    runner = WorkflowRunner(
        workflow_name="tier3-test-runner",
        root_workflow=root_workflow
    )
    result_dict = runner.run(params)
    
    output_data = {}
    for field in Tier3TestRunnerOutput.model_fields.keys():
        if field in result_dict:
            output_data[field] = result_dict[field]
        elif "state" in result_dict and field in result_dict["state"]:
            output_data[field] = result_dict["state"][field]
            
    if not output_data and "value" in Tier3TestRunnerOutput.model_fields:
        output_data["value"] = result_dict.get("message", "success")
        
    return Tier3TestRunnerOutput(**output_data)

