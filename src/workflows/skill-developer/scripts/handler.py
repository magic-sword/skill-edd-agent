from edd_agent_tools import WorkflowRunner
from .models import DevelopSkillOutput
from .workflow import root_workflow

class RuntimeInput:
    """内部引数コンパイル用ダミーオブジェクト。"""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def model_dump(self, **kwargs):
        return self.__dict__


def develop_skill(prompt: str, skill: str | None = None, output_dir: str | None = None, design_path: str | None = None, source_code_dir: str | None = None, target_entry: str | None = None) -> DevelopSkillOutput:
    """新規スキル開発、または既存スキルのリファクタリングを自律的に行うワークフロー。

    Args:
        prompt: スキル設計・実装の要件を記述したプロンプト。
        skill: 対象のスキル名。既存スキルを改修する場合に指定します。
        output_dir: 成果物の出力先ディレクトリのパス。
        design_path: design.jsonの絶対パス。既存スキルを改修する場合に指定します。
        source_code_dir: 実装コードのソースコードディレクトリのパス。既存スキルを改修する場合に指定します。
        target_entry: 優先する論理配置先名。

    Returns:
        実行結果オブジェクト (DevelopSkillOutput)。
    """
    params = RuntimeInput(prompt=prompt, skill=skill, output_dir=output_dir, design_path=design_path, source_code_dir=source_code_dir, target_entry=target_entry)
    runner = WorkflowRunner(
        workflow_name="skill-developer",
        root_workflow=root_workflow
    )
    result_dict = runner.run(params)
    
    output_data = {}
    for field in DevelopSkillOutput.model_fields.keys():
        if field in result_dict:
            output_data[field] = result_dict[field]
        elif "state" in result_dict and field in result_dict["state"]:
            output_data[field] = result_dict["state"][field]
            
    if not output_data and "value" in DevelopSkillOutput.model_fields:
        output_data["value"] = result_dict.get("message", "success")
        
    return DevelopSkillOutput(**output_data)

