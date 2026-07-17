from edd_agent_tools import SkillDesign

class HandlerWriter:
    """
    SkillDesignメタデータから、ADK 2.0 規約準拠の純粋関数（@tool）を含む
    scripts/handler.py のソースコードを決定論的に生成するライター。
    """
    def __init__(self, design: SkillDesign, template_str: str):
        self.design = design
        self.template_str = template_str
        self.is_workflow = (getattr(self.design, "module_type", None) == "workflow")

    def _generate_function_code(self, fn, output_class_name) -> tuple[str, set]:
        args_def_list = []
        args_doc_list = []
        args_pass_list = []
        
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
            args_doc_list.append(f"        {param.name}: {desc}")
            args_pass_list.append(f"{param.name}={param.name}")

        if has_any:
            typing_imports.add("Any")
        if has_literal:
            typing_imports.add("Literal")

        args_definition = ", ".join(args_def_list)
        args_docstring = "\n".join(args_doc_list)
        args_passing = ", ".join(args_pass_list)
        
        if self.is_workflow:
            workflow_name = self.design.name
            func_code = f"""def {fn.name}({args_definition}) -> {output_class_name}:
    \"\"\"{fn.description or ''}

    Args:
{args_docstring}

    Returns:
        実行結果オブジェクト ({output_class_name})。
    \"\"\"
    params = RuntimeInput({args_passing})
    runner = WorkflowRunner(
        workflow_name="{workflow_name}",
        root_workflow=root_workflow
    )
    result_dict = runner.run(params)
    
    output_data = {{}}
    for field in {output_class_name}.model_fields.keys():
        if field in result_dict:
            output_data[field] = result_dict[field]
        elif "state" in result_dict and field in result_dict["state"]:
            output_data[field] = result_dict["state"][field]
            
    if not output_data and "value" in {output_class_name}.model_fields:
        output_data["value"] = result_dict.get("message", "success")
        
    return {output_class_name}(**output_data)"""
        else:
            func_code = f"""def {fn.name}({args_definition}) -> {output_class_name}:
    \"\"\"{fn.description or ''}

    Args:
{args_docstring}

    Returns:
        実行結果オブジェクト ({output_class_name})。
    \"\"\"
    executor = SkillExecutor()
    return executor.{fn.name}({args_passing})"""

        return func_code, typing_imports

    def write(self) -> str:
        if getattr(self.design, "module_type", None) == "workflow" and not getattr(self.design, "functions", None):
            args_def_list = []
            args_doc_list = []
            args_pass_list = []
            
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

        functions_code = []
        all_typing_imports = set()
        output_classes = []
        
        for fn in self.design.functions:
            output_class_name = "".join(part.capitalize() for part in fn.name.replace("-", "_").split("_")) + "Output"
            output_classes.append(output_class_name)
            
            func_code, typing_imports = self._generate_function_code(fn, output_class_name)
            functions_code.append(func_code)
            all_typing_imports.update(typing_imports)
            
        imports = []
        if all_typing_imports:
            unique_imports = sorted(list(all_typing_imports))
            imports.append(f"from typing import {', '.join(unique_imports)}")
        
        imports_str = "\n".join(imports)
        if imports_str:
            imports_str += "\n"
            
        models_import = f"from .models import {', '.join(output_classes)}"
        func_definitions = "\n\n".join(functions_code)
        
        if self.is_workflow:
            runtime_input_def = """class RuntimeInput:
    \"\"\"内部引数コンパイル用ダミーオブジェクト。\"\"\"
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def model_dump(self, **kwargs):
        return self.__dict__"""
            
            return f"""{imports_str}from edd_agent_tools import WorkflowRunner
{models_import}
from .workflow import root_workflow

{runtime_input_def}

{func_definitions}
"""
        else:
            return f"""{imports_str}{models_import}
from .executor import SkillExecutor

{func_definitions}
"""
