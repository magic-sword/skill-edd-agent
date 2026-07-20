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
        
        is_workflow = (getattr(self.design, "module_type", None) == "workflow")
        
        if is_workflow:
            func_name = self.design.name.replace("-", "_")
            class_name = "".join(part.capitalize() for part in func_name.split("_")) + "Output"
            
            output_fields = []
            response_params = getattr(self.design, "response_parameters", None)
            if response_params:
                for param in response_params:
                    field_writer = PydanticFieldWriter(param)
                    output_fields.append(field_writer.to_code())
                    all_typing_imports.update(field_writer.typing_imports)
                output_fields_str = "\n".join(output_fields)
            else:
                output_fields_str = "    value: str = Field(..., description='実行結果の出力メッセージ')"
                
            models_code_str = f"class {class_name}(BaseModel):\n{output_fields_str}"
        else:
            models_code_list = []
            from edd_agent_tools.skills.models import OutputMode
            output_mode = getattr(self.design, "output_mode", OutputMode.STRUCTURED_JSON)
            
            for fn in self.design.functions:
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
            models_code_str = "\n\n".join(models_code_list)
            
        if all_typing_imports:
            unique_imports = sorted(list(all_typing_imports))
            imports.append(f"from typing import {', '.join(unique_imports)}")
            
        imports_str = "\n".join(imports)
        
        custom_template = self.template_str.replace("class Output(BaseModel):", "")
            
        return custom_template.format(
            imports_str=imports_str,
            output_fields_str=models_code_str
        )
