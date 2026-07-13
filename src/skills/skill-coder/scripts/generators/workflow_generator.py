import os
import json
from typing import List

from edd_agent_tools.models import SkillDesign
from ..writer import PydanticModelWriter, HandlerWriter
from .base import BaseCodeGenerator

class WorkflowAgentCodeGenerator(BaseCodeGenerator):
    """
    ワークフローエージェント用のコードおよび決定論的ハーネスを生成する具象クラス。
    """
    def generate(self) -> List[str]:
        self.create_common_directories()
        generated_files = []

        # モジュール名や名前の取得
        workflow_name = self.design.name
        workflow_module_name = workflow_name.replace("-", "_")

        # 1. models.py の自動生成
        models_tmpl = self.coder_skill.load_asset("templates/workflow/models.py.template")
        models_code = PydanticModelWriter(self.design, models_tmpl).write()
        models_path = os.path.join(self.scripts_dir, "models.py")
        with open(models_path, "w", encoding="utf-8") as f:
            f.write(models_code)
        print(f"決定論的モデルファイルを生成しました (workflow): {models_path}")
        generated_files.append(os.path.relpath(models_path, self.target_root_dir))

        # 2. handler.py の自動生成 (templates/workflow/handler.py.template を展開)
        handler_tmpl = self.coder_skill.load_asset("templates/workflow/handler.py.template")
        handler_tmpl = handler_tmpl.replace("{workflow_name}", workflow_name)
        handler_code = HandlerWriter(self.design, handler_tmpl).write()
        handler_path = os.path.join(self.scripts_dir, "handler.py")
        with open(handler_path, "w", encoding="utf-8") as f:
            f.write(handler_code)
        print(f"決定論的ハンドラーファイルを生成しました (workflow): {handler_path}")
        generated_files.append(os.path.relpath(handler_path, self.target_root_dir))

        # 3. __init__.py の自動生成 (templates/workflow/__init__.py.template を展開)
        init_tmpl = self.coder_skill.load_asset("templates/workflow/__init__.py.template")
        init_code = init_tmpl.replace("{workflow_name}", workflow_name).replace("{workflow_module_name}", workflow_module_name)
        init_path = os.path.join(self.scripts_dir, "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(init_code)
        print(f"決定論的パッケージ初期化ファイルを生成しました (workflow): {init_path}")
        generated_files.append(os.path.relpath(init_path, self.target_root_dir))

        # raw design をロードして steps 拡張がないか確認
        raw_design = {}
        try:
            design_file = os.path.join(self.target_root_dir, "assets", "design.json")
            if os.path.exists(design_file):
                with open(design_file, "r", encoding="utf-8") as f:
                    raw_design = json.load(f)
        except Exception:
            pass
            
        steps = raw_design.get("steps", [])

        # 4. workflow.py の生成（steps 定義がある場合は多段階生成、dependencies のみの場合は従来、それ以外はプレースホルダー）
        workflow_path = os.path.join(self.scripts_dir, "workflow.py")
        if steps:
            from edd_agent_tools.skills import SkillsState
            from edd_agent_tools import GeminiClient
            from google.genai import types
            
            state = SkillsState()
            state.load()
            client = GeminiClient()
            
            step_functions = []
            imports_code_lines = []
            
            # 各カスタムノード用の保存ディレクトリを作成
            nodes_dir = os.path.join(self.scripts_dir, "nodes")
            if not os.path.exists(nodes_dir):
                os.makedirs(nodes_dir)
                
            # nodes/__init__.py の生成
            nodes_init_path = os.path.join(nodes_dir, "__init__.py")
            with open(nodes_init_path, "w", encoding="utf-8") as f:
                f.write("# Workflow custom nodes package\n")
            print(f"カスタムノードパッケージ初期化ファイルを生成しました: {nodes_init_path}")
            generated_files.append(os.path.relpath(nodes_init_path, self.target_root_dir))

            # プロンプトアセットのロード
            func_prompt_tmpl = self.coder_skill.load_asset("prompts/function_generator.prompt")
            agent_prompt_tmpl = self.coder_skill.load_asset("prompts/agent_generator.prompt")

            # 【第 1 段階】カスタムノードおよびスキルノードの個別コード生成と別ファイル保存
            for step in steps:
                s_name = step.get("name")
                s_type = step.get("type")
                s_desc = step.get("description", "")
                s_var = s_name.replace("-", "_")
                func_name = f"run_{s_var}_step"
                step_functions.append(func_name)
                
                node_file_path = os.path.join(nodes_dir, f"{s_var}.py")
                imports_code_lines.append(f"from .nodes.{s_var} import {func_name}")
                
                if s_type == "skill":
                    target_skill = step.get("target")
                    dep_var = target_skill.replace("-", "_")
                    
                    # 依存スキルの入力をロードしてパラメータ名を抽出する
                    dep_input_params = []
                    try:
                        dep_skill = state.get_skill(target_skill)
                        dep_design = dep_skill.load_design()
                        dep_input_params = [p.name for p in dep_design.parameters]
                    except Exception as e:
                        print(f"警告: 依存スキル {target_skill} の設計ロードに失敗しました: {e}")
                    
                    # inputs マッピング
                    dep_mapping = step.get("inputs", {})
                    param_assignments = []
                    for param_name, mapping_val in dep_mapping.items():
                        is_expression = (
                            "tool_context" in mapping_val or 
                            "(" in mapping_val or 
                            ")" in mapping_val or 
                            "+" in mapping_val or
                            "*" in mapping_val or
                            "/" in mapping_val or
                            " " in mapping_val or
                            "." in mapping_val
                        )
                        if is_expression:
                            param_assignments.append(f'        {param_name}={mapping_val}')
                        else:
                            param_assignments.append(f'        {param_name}=tool_context.state.get("{mapping_val}")')
                    
                    # 指定されていない必要なパラメータを state.get() で自動補完
                    assigned_names = set(dep_mapping.keys())
                    for required_param in dep_input_params:
                        if required_param not in assigned_names:
                            param_assignments.append(f'        {required_param}=tool_context.state.get("{required_param}")')
                            
                    params_init_str = ",\n".join(param_assignments)
                    
                    node_lines = [
                        "from google.adk.tools import ToolContext",
                        "from edd_agent_tools.skills import SkillsState",
                        "import json",
                        "",
                        "state = SkillsState()",
                        "state.load()",
                        f'{dep_var}_module = state.get_skill("{target_skill}").load_module()',
                        "",
                        f"def {func_name}(tool_context: ToolContext) -> str:",
                        "    # 設計書の inputs マッピングから直接決定論的に引数を抽出"
                    ]
                    
                    # 個別引数の具象関数を直接呼び出すコードを組み立てる
                    node_lines.append(f"    res = {dep_var}_module.{dep_var}(")
                    if params_init_str:
                        node_lines.append(params_init_str)
                    node_lines.append("    )")
                    
                    node_lines.append("    from pydantic import BaseModel")
                    node_lines.append("    if isinstance(res, BaseModel):")
                    node_lines.append("        tool_context.state.update(res.model_dump())")
                    node_lines.append("        res_str = res.model_dump_json()")
                    node_lines.append("    elif isinstance(res, dict):")
                    node_lines.append("        tool_context.state.update(res)")
                    node_lines.append("        res_str = json.dumps(res)")
                    node_lines.append("    else:")
                    node_lines.append("        res_str = str(res)")
                    node_lines.append("    return res_str")
                    node_lines.append("")
                    
                    node_code = "\n".join(node_lines)
                    with open(node_file_path, "w", encoding="utf-8") as f:
                        f.write(node_code)
                    print(f"他スキル呼び出しノードを書き出しました: {node_file_path}")
                    generated_files.append(os.path.relpath(node_file_path, self.target_root_dir))
                    
                elif s_type == "function":
                    prompt = func_prompt_tmpl.format(func_name=func_name, s_desc=s_desc)
                    print(f"Gemini API でカスタム関数ノード {func_name} を生成中...")
                    try:
                        res = client.generate_content(
                            contents=prompt,
                            config=types.GenerateContentConfig(temperature=0.1)
                        )
                        func_code = res.text
                        if "```" in func_code:
                            func_code = "\n".join([line for line in func_code.split("\n") if not line.strip().startswith("```")])
                        
                        with open(node_file_path, "w", encoding="utf-8") as f:
                            f.write(func_code)
                        print(f"カスタム関数ノードを書き出しました: {node_file_path}")
                        generated_files.append(os.path.relpath(node_file_path, self.target_root_dir))
                    except Exception as e:
                        print(f"警告: 関数ノード生成に失敗しました: {e}")
                        
                elif s_type == "agent":
                    s_instruction = step.get("instruction", "指示に従って処理を実行してください。")
                    s_tools = step.get("tools", [])
                    prompt = agent_prompt_tmpl.format(
                        func_name=func_name,
                        s_var=s_var,
                        s_instruction=s_instruction,
                        s_tools=s_tools
                    )
                    print(f"Gemini API でエージェントノード {func_name} を生成中...")
                    try:
                        res = client.generate_content(
                            contents=prompt,
                            config=types.GenerateContentConfig(temperature=0.1)
                        )
                        agent_code = res.text
                        if "```" in agent_code:
                            agent_code = "\n".join([line for line in agent_code.split("\n") if not line.strip().startswith("```")])
                        
                        with open(node_file_path, "w", encoding="utf-8") as f:
                            f.write(agent_code)
                        print(f"エージェントノードを書き出しました: {node_file_path}")
                        generated_files.append(os.path.relpath(node_file_path, self.target_root_dir))
                    except Exception as e:
                        print(f"警告: エージェントノード生成に失敗しました: {e}")
            # 【第 2 段階】100%決定論的な組み立て
            code_lines = [
                '"""',
                f'{workflow_name} の Workflow オブジェクト定義。',
                'ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した多段階接続。',
                '"""',
                'from google.adk import Workflow',
                ''
            ]
            
            # インポート
            code_lines.extend(imports_code_lines)
            code_lines.append('')
            
            # edgesの構築
            code_lines.append("root_workflow = Workflow(")
            code_lines.append(f'    name="{workflow_module_name}",')
            code_lines.append("    edges=[")
            code_lines.append(f'        ("START", {step_functions[0]}),')
            for i in range(len(step_functions) - 1):
                code_lines.append(f'        ({step_functions[i]}, {step_functions[i+1]}),')
            code_lines.append("    ]")
            code_lines.append(")")
            
            workflow_code = "\n".join(code_lines)
            
        elif self.design.dependencies:
            from edd_agent_tools.skills import SkillsState
            from edd_agent_tools import GeminiClient
            from google.genai import types
            
            state = SkillsState()
            state.load()
            client = GeminiClient()
            
            step_functions = []
            imports_code_lines = []
            
            # 各依存スキルのスキーマからマッピングコードを組み立てる
            schema_docs = []
            for dep in self.design.dependencies:
                try:
                    dep_skill = state.get_skill(dep)
                    dep_design = dep_skill.load_design()
                    
                    inputs = []
                    for param in dep_design.input_parameters:
                        inputs.append(f"  - {param.name} ({param.type}): {param.description}")
                        
                    outputs = []
                    for param in dep_design.response_parameters:
                        outputs.append(f"  - {param.name} ({param.type}): {param.description}")
                        
                    inputs_str = "\n".join(inputs) if inputs else "  なし"
                    outputs_str = "\n".join(outputs) if outputs else "  なし"
                    
                    schema_docs.append(
                        f"■ スキル名: {dep_design.name}\n"
                        f"説明: {dep_design.description}\n"
                        f"入力パラメータ (Input):\n{inputs_str}\n"
                        f"出力パラメータ (Output):\n{outputs_str}\n"
                    )
                except Exception as e:
                    print(f"警告: 依存スキル {dep} のスキーマ取得に失敗しました: {e}")
            
            workflow_design_str = json.dumps(self.design.model_dump(), indent=2, ensure_ascii=False)
            
            prompt_tmpl = self.coder_skill.load_asset("prompts/workflow_generator.prompt")
            prompt = prompt_tmpl.replace(
                "{dependency_schemas_str}", "\n".join(schema_docs)
            ).replace(
                "{module_name}", workflow_name
            ).replace(
                "{workflow_design_str}", workflow_design_str
            )
            
            print(f"Gemini API を呼び出して {workflow_name} 用のパラメータマッピング情報を生成しています...")
            mapping_data = {}
            try:
                response = client.generate_content(
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json"
                    )
                )
                mapping_json_str = response.text
                if "```" in mapping_json_str:
                    mapping_json_str = "\n".join([line for line in mapping_json_str.split("\n") if not line.strip().startswith("```")])
                mapping_data = json.loads(mapping_json_str)
            except Exception as e:
                print(f"警告: パラメータマッピングの生成に失敗しました: {e}")
                
            code_lines = [
                '"""',
                f'{workflow_name} の Workflow オブジェクト定義。',
                'ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠した関数ノード接続。',
                '"""',
                'from google.adk import Workflow',
                'from google.adk.tools import ToolContext',
                'from edd_agent_tools.skills import SkillsState',
                'import json',
                '',
                'state = SkillsState()',
                'state.load()',
                ''
            ]
            
            for dep in self.design.dependencies:
                dep_var = dep.replace("-", "_")
                imports_code_lines.append(f'{dep_var}_module = state.get_skill("{dep}").load_module()')
                
            code_lines.extend(imports_code_lines)
            code_lines.append('')
            
            for dep in self.design.dependencies:
                dep_var = dep.replace("-", "_")
                func_name = f"run_{dep_var}_step"
                step_functions.append(func_name)
                
                code_lines.append(f"def {func_name}(tool_context: ToolContext) -> str:")
                code_lines.append("    # セマンティックにマッピングされた引数の抽出")
                
                dep_mapping = mapping_data.get(dep, {})
                param_assignments = []
                for param_name, mapping_val in dep_mapping.items():
                    is_expression = (
                        "tool_context" in mapping_val or 
                        "(" in mapping_val or 
                        ")" in mapping_val or 
                        "+" in mapping_val or
                        "*" in mapping_val or
                        "/" in mapping_val or
                        " " in mapping_val or
                        "." in mapping_val
                    )
                    if is_expression:
                        param_assignments.append(f'        {param_name}={mapping_val}')
                    else:
                        param_assignments.append(f'        {param_name}=tool_context.state.get("{mapping_val}")')
                        
                params_init_str = ",\n".join(param_assignments)
                code_lines.append(f"    res = {dep_var}_module.{dep_var}(")
                if params_init_str:
                    code_lines.append(params_init_str)
                code_lines.append("    )")
                
                code_lines.append("    from pydantic import BaseModel")
                code_lines.append("    if isinstance(res, BaseModel):")
                code_lines.append("        tool_context.state.update(res.model_dump())")
                code_lines.append("        res_str = res.model_dump_json()")
                code_lines.append("    elif isinstance(res, dict):")
                code_lines.append("        tool_context.state.update(res)")
                code_lines.append("        res_str = json.dumps(res)")
                code_lines.append("    else:")
                code_lines.append("        res_str = str(res)")
                code_lines.append("    return res_str")
                code_lines.append("")
                
            # edgesの生成
            code_lines.append("root_workflow = Workflow(")
            code_lines.append(f'    name="{workflow_module_name}",')
            code_lines.append("    edges=[")
            code_lines.append(f'        ("START", {step_functions[0]}),')
            for i in range(len(step_functions) - 1):
                code_lines.append(f'        ({step_functions[i]}, {step_functions[i+1]}),')
            code_lines.append("    ]")
            code_lines.append(")")
            
            workflow_code = "\n".join(code_lines)
        else:
            workflow_tmpl = self.coder_skill.load_asset("templates/workflow/workflow.py.template")
            workflow_code = workflow_tmpl.replace("{workflow_name}", workflow_name).replace("{workflow_module_name}", workflow_module_name)

        with open(workflow_path, "w", encoding="utf-8") as f:
            f.write(workflow_code)
        print(f"workflow.py を生成しました: {workflow_path}")
        generated_files.append(os.path.relpath(workflow_path, self.target_root_dir))
        return generated_files
