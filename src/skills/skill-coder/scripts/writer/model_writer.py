from edd_agent_tools import SkillDesign
from .base import PydanticFieldWriter

class PydanticModelWriter:
    """
    SkillDesignメタデータから、Pydantic Outputクラス定義を含む
    scripts/models.py のソースコードを決定論的に生成するライター。
    """
    def __init__(self, design: SkillDesign, template_str: str):
        self.design = design
        self.template_str = template_str

    def write(self) -> str:
        imports = ["from pydantic import BaseModel, Field"]
        all_typing_imports = set()
        
        if getattr(self.design, "module_type", None) == "workflow":
            output_fields = []
            for param in self.design.response_parameters or []:
                field_writer = PydanticFieldWriter(param)
                output_fields.append(field_writer.to_code())
                all_typing_imports.update(field_writer.typing_imports)

            if all_typing_imports:
                unique_imports = sorted(list(all_typing_imports))
                imports.append(f"from typing import {', '.join(unique_imports)}")
                
            imports_str = "\n".join(imports)
            output_fields_str = "\n".join(output_fields) if output_fields else "    value: str = Field(..., description='実行結果の出力メッセージ')"
            
            return self.template_str.format(
                imports_str=imports_str,
                output_fields_str=output_fields_str
            )
            
        models_code_list = []
        from edd_agent_tools.skills.models import OutputMode
        output_mode = getattr(self.design, "output_mode", OutputMode.STRUCTURED_JSON)
        
        for fn in self.design.functions:
            # 関数名をキャメルケース of Output クラス名に変換
            class_name = "".join(part.capitalize() for part in fn.name.replace("-", "_").split("_")) + "Output"
            
            if fn.response_parameters and output_mode == OutputMode.STRUCTURED_JSON:
                output_fields = []
                for param in fn.response_parameters:
                    field_writer = PydanticFieldWriter(param)
                    output_fields.append(field_writer.to_code())
                    all_typing_imports.update(field_writer.typing_imports)
                output_fields_str = "\n".join(output_fields)
            else:
                output_fields_str = "    value: str = Field(..., description='実行結果の出力メッセージ')"
                
            model_code = f"class {class_name}(BaseModel):\n{output_fields_str}"
            models_code_list.append(model_code)
            
        # 必要なタイピングインポートを追加
        if all_typing_imports:
            unique_imports = sorted(list(all_typing_imports))
            imports.append(f"from typing import {', '.join(unique_imports)}")
            
        imports_str = "\n".join(imports)
        
        # class Output(BaseModel): という文字列部分を削除して複数モデルで置き換える
        custom_template = self.template_str.replace("class Output(BaseModel):", "")
        models_code_str = "\n\n".join(models_code_list)
        if models_code_list:
            models_code_str += f"\n\nOutput = {class_name}"
            
        return custom_template.format(
            imports_str=imports_str,
            output_fields_str=models_code_str
        )
