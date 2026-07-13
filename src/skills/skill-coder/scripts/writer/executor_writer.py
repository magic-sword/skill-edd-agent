from edd_agent_tools.models import SkillDesign

class ExecutorWriter:
    """
    SkillDesignメタデータから、ビジネスロジックエントリポイントである
    scripts/executor.py のプレースホルダーソースコードを決定論的に生成するライター。
    """
    def __init__(self, design: SkillDesign, template_str: str):
        self.design = design
        self.template_str = template_str

    def _generate_method_code(self, fn, output_class_name) -> tuple[str, set]:
        args_def_list = []
        args_doc_list = []
        has_literal = False
        has_any = False
        typing_imports = set()
        
        sorted_params = sorted(fn.parameters, key=lambda p: not p.required)
        
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

        if has_any:
            typing_imports.add("Any")
        if has_literal:
            typing_imports.add("Literal")

        args_definition = ", ".join(["self"] + args_def_list)
        args_docstring = "\n".join(args_doc_list)
        
        method_code = f"""    def {fn.name}({args_definition}) -> {output_class_name}:
        \"\"\"{fn.description or ''}

        Args:
{args_docstring}

        Returns:
            処理結果の構造化データ（{output_class_name}）。
        \"\"\"
        # TODO: ロジックの実装
        raise NotImplementedError()"""

        return method_code, typing_imports

    def write(self) -> str:
        if getattr(self.design, "module_type", None) == "workflow":
            args_def_list = []
            args_doc_list = []
            args_assign_list = []
            
            has_literal = False
            has_any = False
            
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

        methods_code = []
        all_typing_imports = set()
        output_classes = []
        
        for fn in self.design.functions:
            output_class_name = "".join(part.capitalize() for part in fn.name.replace("-", "_").split("_")) + "Output"
            output_classes.append(output_class_name)
            
            method_code, typing_imports = self._generate_method_code(fn, output_class_name)
            methods_code.append(method_code)
            all_typing_imports.update(typing_imports)
            
        imports = []
        if all_typing_imports:
            unique_imports = sorted(list(all_typing_imports))
            imports.append(f"from typing import {', '.join(unique_imports)}")
        
        imports_str = "\n".join(imports)
        if imports_str:
            imports_str += "\n"
            
        models_import = f"from .models import {', '.join(output_classes)}"
        method_definitions = "\n\n".join(methods_code)
        
        return f"""{imports_str}{models_import}

class SkillExecutor:
    \"\"\"ビジネスロジックを責務ごとに分割して実行するオブジェクト指向エグゼキューター。\"\"\"

    def __init__(self):
        \"\"\"SkillExecutor を初期化します。\"\"\"
        pass

{method_definitions}
"""
