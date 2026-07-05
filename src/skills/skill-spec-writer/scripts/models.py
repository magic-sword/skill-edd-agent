from pydantic import BaseModel, Field, model_validator

class Input(BaseModel):
    design_path: str | None = Field(None, description="design.json ファイルの直接のパス。省略された場合は skill から自動探索します。")
    skill: str | None = Field(None, description="対象の既存スキル名。design_path 省略時の自動探索キーとして使用されます。")
    output_dir: str | None = Field(None, description="生成されたSKILL.mdを保存するディレクトリのパス。省略時は対象スキルのディレクトリに出力されます。")
    source_code_dir: str | None = Field(None, description="実装ソースコードが格納されたディレクトリパス（または単一ファイル）。指定しない場合、自動的にスキルの scripts ディレクトリを探索します。")

    @model_validator(mode="after")
    def check_skill_or_design_path(self) -> "Input":
        """skill と design_path のいずれか一方は必ず指定する必要があります。"""
        if not self.skill and not self.design_path:
            raise ValueError("Either 'skill' or 'design_path' must be provided.")
        return self
