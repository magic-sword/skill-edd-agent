import json
from edd_agent_tools.models import SkillDesign

class PydanticModelWriter:
    """
    SkillDesignメタデータから、Pydantic Inputクラス定義を含む
    scripts/models.py のソースコードを決定論的に生成するライター。
    """
    def __init__(self, design: SkillDesign, template_str: str):
        self.design = design
        self.template_str = template_str

    def write(self) -> str:
        fields = []
        has_any = False
        
        for param in self.design.parameters:
            t_str = param.type.strip().lower()
            if t_str == "str":
                python_type = "str"
            elif t_str == "int":
                python_type = "int"
            elif t_str == "bool":
                python_type = "bool"
            elif t_str == "float":
                python_type = "float"
            elif t_str == "list":
                python_type = "list"
            else:
                python_type = "Any"
                has_any = True
                
            if param.required:
                default_expr = "..."
                annotated_type = python_type
            else:
                if param.default is None:
                    default_expr = "None"
                    annotated_type = f"{python_type} | None"
                else:
                    annotated_type = python_type
                    if t_str == "str":
                        default_expr = repr(param.default)
                    elif t_str == "bool":
                        default_expr = "True" if str(param.default).lower() in ("true", "1", "yes") else "False"
                    elif t_str in ("int", "float"):
                        default_expr = str(param.default)
                    else:
                        default_expr = repr(param.default)
                        
            field_str = f"    {param.name}: {annotated_type} = Field({default_expr}, description={repr(param.description)})"
            fields.append(field_str)
            
        fields_str = "\n".join(fields) if fields else "    pass"
        return self.template_str.format(fields_str=fields_str)

class HandlerWriter:
    """
    SkillDesignメタデータから、薄いルーティング処理を含む
    scripts/handler.py のソースコードを決定論的に生成するライター。
    """
    def __init__(self, design: SkillDesign, template_str: str):
        self.design = design
        self.template_str = template_str

    def write(self) -> str:
        metadata = {
            "name": self.design.name,
            "description": self.design.description,
            "execution_type": self.design.execution_type,
            "output_mode": self.design.output_mode,
            "dependencies": self.design.dependencies
        }
        metadata_str = json.dumps(metadata, indent=4, ensure_ascii=False)
        any_import = ""
        return self.template_str.format(
            any_import=any_import,
            metadata_str=metadata_str
        )
