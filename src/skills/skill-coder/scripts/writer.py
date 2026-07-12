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
    SkillDesignメタデータから、Pydantic Outputクラス定義を含む
    scripts/models.py のソースコードを決定論的に生成するライター。
    """
    def __init__(self, design: SkillDesign, template_str: str):
        self.design = design
        self.template_str = template_str

    def write(self) -> str:
        imports = ["from pydantic import BaseModel, Field"]
        all_typing_imports = set()
        
        # Output クラスのインナーフィールド生成
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
        
        # テンプレートにマッピングして出力
        return self.template_str.format(
            imports_str=imports_str,
            output_fields_str=output_fields_str
        )

class HandlerWriter:
    """
    SkillDesignメタデータから、ADK 2.0 規約準拠の純粋関数（@tool）を含む
    scripts/handler.py のソースコードを決定論的に生成するライター。
    """
    def __init__(self, design: SkillDesign, template_str: str):
        self.design = design
        self.template_str = template_str

    def write(self) -> str:
        args_def_list = []
        args_doc_list = []
        args_pass_list = []
        
        has_literal = False
        has_any = False
        
        # 必須引数を先、デフォルト値ありを後にソート
        sorted_params = sorted(self.design.parameters, key=lambda p: not p.required)
        
        for param in sorted_params:
            type_str = "Any"
            if param.choices:
                choices_expr = ", ".join(repr(c) if isinstance(c, str) else str(c) for c in param.choices)
                type_str = f"Literal[{choices_expr}]"
                has_literal = True
            else:
                t_str = param.type.strip().lower()
                if t_str == "list":
                    if param.items_type:
                        inner_type = param.items_type.strip().lower()
                        if inner_type in ("str", "int", "bool", "float"):
                            type_str = f"list[{inner_type}]"
                        else:
                            type_str = "list[Any]"
                            has_any = True
                    else:
                        type_str = "list"
                elif t_str in ("str", "int", "bool", "float"):
                    type_str = t_str
                else:
                    type_str = "Any"
                    has_any = True

            if not param.required and param.default is None:
                type_str = f"{type_str} | None"

            if param.required:
                arg_expr = f"{param.name}: {type_str}"
            else:
                if param.default is None:
                    default_val = "None"
                elif isinstance(param.default, bool):
                    default_val = "True" if param.default else "False"
                elif isinstance(param.default, (int, float)):
                    default_val = str(param.default)
                elif isinstance(param.default, str):
                    default_val = repr(param.default)
                else:
                    default_val = repr(param.default)
                arg_expr = f"{param.name}: {type_str} = {default_val}"

            args_def_list.append(arg_expr)
            
            desc = param.description or ""
            args_doc_list.append(f"        {param.name}: {desc}")
            
            args_pass_list.append(f"{param.name}={param.name}")

        imports = []
        typing_imports = []
        if has_any:
            typing_imports.append("Any")
        if has_literal:
            typing_imports.append("Literal")
        if typing_imports:
            imports.append(f"from typing import {', '.join(typing_imports)}")

        imports_str = "\n".join(imports)
        if imports_str:
            imports_str += "\n"

        args_definition = ", ".join(args_def_list)
        args_docstring = "\n".join(args_doc_list)
        args_passing = ", ".join(args_pass_list)
        function_name = self.design.name.replace("-", "_")

        return self.template_str.format(
            imports_str=imports_str,
            function_name=function_name,
            args_definition=args_definition,
            args_docstring=args_docstring,
            args_passing=args_passing,
            description=self.design.description or ""
        )

class ExecutorWriter:
    """
    SkillDesignメタデータから、ビジネスロジックエントリポイントである
    scripts/executor.py のプレースホルダーソースコードを決定論的に生成するライター。
    """
    def __init__(self, design: SkillDesign, template_str: str):
        self.design = design
        self.template_str = template_str

    def write(self) -> str:
        args_def_list = []
        args_doc_list = []
        args_assign_list = []
        
        has_literal = False
        has_any = False
        
        # 必須引数を先、デフォルト値ありを後にソート
        sorted_params = sorted(self.design.parameters, key=lambda p: not p.required)
        
        for param in sorted_params:
            type_str = "Any"
            if param.choices:
                choices_expr = ", ".join(repr(c) if isinstance(c, str) else str(c) for c in param.choices)
                type_str = f"Literal[{choices_expr}]"
                has_literal = True
            else:
                t_str = param.type.strip().lower()
                if t_str == "list":
                    if param.items_type:
                        inner_type = param.items_type.strip().lower()
                        if inner_type in ("str", "int", "bool", "float"):
                            type_str = f"list[{inner_type}]"
                        else:
                            type_str = "list[Any]"
                            has_any = True
                    else:
                        type_str = "list"
                elif t_str in ("str", "int", "bool", "float"):
                    type_str = t_str
                else:
                    type_str = "Any"
                    has_any = True

            if not param.required and param.default is None:
                type_str = f"{type_str} | None"

            if param.required:
                arg_expr = f"{param.name}: {type_str}"
            else:
                if param.default is None:
                    default_val = "None"
                elif isinstance(param.default, bool):
                    default_val = "True" if param.default else "False"
                elif isinstance(param.default, (int, float)):
                    default_val = str(param.default)
                elif isinstance(param.default, str):
                    default_val = repr(param.default)
                else:
                    default_val = repr(param.default)
                arg_expr = f"{param.name}: {type_str} = {default_val}"

            args_def_list.append(arg_expr)
            
            desc = param.description or ""
            args_doc_list.append(f"            {param.name}: {desc}")
            
            args_assign_list.append(f"        self.{param.name} = {param.name}")

        imports = []
        typing_imports = []
        if has_any:
            typing_imports.append("Any")
        if has_literal:
            typing_imports.append("Literal")
        if typing_imports:
            imports.append(f"from typing import {', '.join(typing_imports)}")

        imports_str = "\n".join(imports)
        if imports_str:
            imports_str += "\n"

        args_definition = ", ".join(args_def_list)
        args_docstring = "\n".join(args_doc_list)
        args_assignment = "\n".join(args_assign_list) if args_assign_list else "        pass"

        return self.template_str.format(
            imports_str=imports_str,
            args_definition=args_definition,
            args_docstring=args_docstring,
            args_assignment=args_assignment
        )
