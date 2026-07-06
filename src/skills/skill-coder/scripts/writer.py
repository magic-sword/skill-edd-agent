import json
from edd_agent_tools.models import SkillDesign, Parameter

class PydanticFieldWriter:
    """
    1つの Parameter 情報から、Pydantic のフィールド定義コード行を生成するライター。
    """
    def __init__(self, param: Parameter):
        self.param = param
        self.typing_imports = set()

    def to_code(self) -> str:
        """Pydanticの属性定義のコード文字列（例: 'prompt: str = Field(...)'）を返します。"""
        type_expr = self._resolve_type()
        # 非必須かつデフォルト値が明示されていない場合は Union 型にマージ (| None)
        if not self.param.required and self.param.default is None:
            type_expr = f"{type_expr} | None"
            
        if getattr(self.param, "is_prompt_parameter", False):
            args_expr = self._resolve_prompt_field_args()
            return f"    {self.param.name}: {type_expr} = PromptField({args_expr})"
        else:
            args_expr = self._resolve_field_args()
            return f"    {self.param.name}: {type_expr} = Field({args_expr})"

    def _resolve_type(self) -> str:
        # 1. 選択肢指定 (Literal)
        if self.param.choices:
            self.typing_imports.add("Literal")
            choices_expr = ", ".join(repr(c) if isinstance(c, str) else str(c) for c in self.param.choices)
            return f"Literal[{choices_expr}]"

        # 2. リスト型 (items_type による要素型指定の解決)
        t_str = self.param.type.strip().lower()
        if t_str == "list":
            if self.param.items_type:
                inner_type = self.param.items_type.strip().lower()
                if inner_type == "str":
                    return "list[str]"
                elif inner_type == "int":
                    return "list[int]"
                elif inner_type == "bool":
                    return "list[bool]"
                elif inner_type == "float":
                    return "list[float]"
                else:
                    self.typing_imports.add("Any")
                    return "list[Any]"
            return "list"

        # 3. 基本型
        if t_str == "str":
            return "str"
        elif t_str == "int":
            return "int"
        elif t_str == "bool":
            return "bool"
        elif t_str == "float":
            return "float"
        else:
            self.typing_imports.add("Any")
            return "Any"

    def _resolve_field_args(self) -> str:
        # 必須・非必須に基づくデフォルト値表現
        if self.param.required:
            default_expr = "..."
        else:
            if self.param.default is None:
                default_expr = "None"
            else:
                t_str = self.param.type.strip().lower() if not self.param.choices else "choices"
                if t_str == "str":
                    default_expr = repr(self.param.default)
                elif t_str == "bool":
                    default_expr = "True" if str(self.param.default).lower() in ("true", "1", "yes") else "False"
                elif t_str in ("int", "float"):
                    default_expr = str(self.param.default)
                else:
                    default_expr = repr(self.param.default)

        # オプションパラメータ（制約、説明）の組み立て
        field_args = []
        if self.param.ge is not None:
            field_args.append(f"ge={self.param.ge}")
        if self.param.le is not None:
            field_args.append(f"le={self.param.le}")
        if self.param.pattern is not None:
            field_args.append(f"pattern={repr(self.param.pattern)}")
        if self.param.min_length is not None:
            field_args.append(f"min_length={self.param.min_length}")
        if self.param.max_length is not None:
            field_args.append(f"max_length={self.param.max_length}")

        desc_val = self.param.description or ""
        field_args.append(f"description={repr(desc_val)}")

        return ", ".join([default_expr] + field_args)

    def _resolve_prompt_field_args(self) -> str:
        # 必須・非必須に基づくデフォルト値表現
        if self.param.required:
            default_expr = "..."
        else:
            if self.param.default is None:
                default_expr = "None"
            else:
                default_expr = repr(self.param.default)

        field_args = [default_expr]
        
        # description
        desc_val = self.param.description or ""
        field_args.append(f"description={repr(desc_val)}")
        
        # instructions
        inst_val = getattr(self.param, "prompt_instructions", None) or ""
        field_args.append(f"instructions={repr(inst_val)}")
        
        # constraints
        cons_val = getattr(self.param, "prompt_constraints", None) or ""
        field_args.append(f"constraints={repr(cons_val)}")
        
        return ", ".join(field_args)

class PydanticModelWriter:
    """
    SkillDesignメタデータから、Pydantic Input/Outputクラス定義を含む
    scripts/models.py のソースコードを決定論的に生成するライター。
    """
    def __init__(self, design: SkillDesign, template_str: str):
        self.design = design
        self.template_str = template_str

    def write(self) -> str:
        fields = []
        
        # パラメータ内に PromptField 対象があるかチェック
        has_prompt_param = any(getattr(p, "is_prompt_parameter", False) for p in self.design.parameters)
        
        imports = ["from pydantic import BaseModel, Field"]
        if has_prompt_param:
            imports.append("from edd_agent_tools.models import PromptField")
            
        all_typing_imports = set()
        
        # 1. Input クラス用のフィールド生成
        for param in self.design.parameters:
            field_writer = PydanticFieldWriter(param)
            fields.append(field_writer.to_code())
            all_typing_imports.update(field_writer.typing_imports)
            
        fields_str = "\n".join(fields) if fields else "    pass"

        # 2. Output クラスのインナーフィールド生成
        from edd_agent_tools.models import OutputMode
        output_mode = getattr(self.design, "output_mode", OutputMode.STRUCTURED_JSON)
        if self.design.response_parameters and output_mode == OutputMode.STRUCTURED_JSON:
            output_fields = []
            for param in self.design.response_parameters:
                field_writer = PydanticFieldWriter(param)
                output_fields.append(field_writer.to_code())
                all_typing_imports.update(field_writer.typing_imports)
                
            output_fields_str = "\n".join(output_fields) if output_fields else "    pass"
        else:
            output_fields_str = "    value: str = Field(..., description='スキル実行結果の出力メッセージ')"
            
        # 必要なタイピングインポートを追加
        if all_typing_imports:
            unique_imports = sorted(list(all_typing_imports))
            imports.append(f"from typing import {', '.join(unique_imports)}")
            
        imports_str = "\n".join(imports)
        
        # 3. テンプレートにマッピングして出力
        return self.template_str.format(
            imports_str=imports_str,
            input_fields_str=fields_str,
            output_fields_str=output_fields_str
        )

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
        }
        if getattr(self.design, "summary", None):
            metadata["summary"] = self.design.summary

        metadata.update({
            "execution_type": getattr(self.design, "execution_type", "agent"),
            "output_mode": getattr(self.design, "output_mode", "STRUCTURED_JSON"),
            "dependencies": self.design.dependencies
        })
        metadata_str = json.dumps(metadata, indent=4, ensure_ascii=False)
        any_import = ""
        return self.template_str.format(
            any_import=any_import,
            metadata_str=metadata_str
        )
