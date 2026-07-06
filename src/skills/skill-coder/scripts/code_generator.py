import os
import json
from abc import ABC, abstractmethod
from typing import List

from edd_agent_tools.skills import Skill
from edd_agent_tools.models import SkillDesign, ModuleType
from .writer import PydanticModelWriter, HandlerWriter

class BaseCodeGenerator(ABC):
    """
    コードファイル自動生成の抽象基底クラス。
    """
    def __init__(self, 
                 design: SkillDesign, 
                 target_root_dir: str, 
                 coder_skill: Skill):
        self.design = design
        self.target_root_dir = target_root_dir
        self.scripts_dir = os.path.join(target_root_dir, "scripts")
        self.coder_skill = coder_skill

    def create_common_directories(self):
        """共通ディレクトリの作成"""
        os.makedirs(self.scripts_dir, exist_ok=True)
        os.makedirs(os.path.join(self.target_root_dir, "assets"), exist_ok=True)
        os.makedirs(os.path.join(self.target_root_dir, "references"), exist_ok=True)

    @abstractmethod
    def generate(self) -> List[str]:
        """各モジュールタイプに応じた具体的なコード生成処理"""
        pass


class ToolSkillCodeGenerator(BaseCodeGenerator):
    """
    決定論的スキル（従来どおりのtool）用のコードを生成する具象クラス。
    """
    def generate(self) -> List[str]:
        self.create_common_directories()
        generated_files = []

        # 1. models.py の自動生成
        models_tmpl = self.coder_skill.load_asset("templates/tool/models.py.template")
        models_code = PydanticModelWriter(self.design, models_tmpl).write()
        models_path = os.path.join(self.scripts_dir, "models.py")
        with open(models_path, "w", encoding="utf-8") as f:
            f.write(models_code)
        print(f"決定論的モデルファイルを生成しました: {models_path}")
        generated_files.append(os.path.relpath(models_path, self.target_root_dir))
    
        # 2. handler.py の自動生成
        handler_tmpl = self.coder_skill.load_asset("templates/tool/handler.py.template")
        handler_code = HandlerWriter(self.design, handler_tmpl).write()
        handler_path = os.path.join(self.scripts_dir, "handler.py")
        with open(handler_path, "w", encoding="utf-8") as f:
            f.write(handler_code)
        print(f"決定論的ハンドラーファイルを生成しました: {handler_path}")
        generated_files.append(os.path.relpath(handler_path, self.target_root_dir))

        # 3. __init__.py の決定論的自動生成 (テンプレートのコピー)
        init_tmpl = self.coder_skill.load_asset("templates/tool/__init__.py.template")
        init_path = os.path.join(self.scripts_dir, "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(init_tmpl)
        print(f"決定論的パッケージ初期化ファイルを生成しました: {init_path}")
        generated_files.append(os.path.relpath(init_path, self.target_root_dir))

        # 4. executor.py のプレースホルダー配置（存在しない場合のみ）
        executor_path = os.path.join(self.scripts_dir, "executor.py")
        if not os.path.exists(executor_path):
            executor_tmpl = self.coder_skill.load_asset("templates/tool/executor.py.template")
            with open(executor_path, "w", encoding="utf-8") as f:
                f.write(executor_tmpl)
            print(f"executor.py のプレースホルダーを配置しました: {executor_path}")
            generated_files.append(os.path.relpath(executor_path, self.target_root_dir))
            
        return generated_files


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

        # 4. workflow.py の生成（依存関係がある場合はセマンティック生成、なければプレースホルダー）
        workflow_path = os.path.join(self.scripts_dir, "workflow.py")
        if self.design.dependencies:
            from edd_agent_tools.skills import SkillsState
            from edd_agent_tools import GeminiClient
            from google.genai import types
            
            state = SkillsState()
            state.load()
            
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
            client = GeminiClient()
            try:
                response = client.generate_content(
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json"
                    )
                )
                mapping_json_str = response.text
                
                # markdownコードブロックを念のため除去
                if "```" in mapping_json_str:
                    lines = mapping_json_str.split("\n")
                    cleaned_lines = []
                    in_block = False
                    for line in lines:
                        if line.strip().startswith("```"):
                            in_block = not in_block
                            continue
                        cleaned_lines.append(line)
                    mapping_json_str = "\n".join(cleaned_lines)
                
                mapping_data = json.loads(mapping_json_str)
                print("生成されたマッピング定義:", mapping_data)
                
                # 決定論的な Python コードの組み立て
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
                
                # モジュールインポートの生成
                for dep in self.design.dependencies:
                    dep_var = dep.replace("-", "_")
                    code_lines.append(f'{dep_var}_module = state.get_skill("{dep}").load_module()')
                
                code_lines.append('')
                
                # 関数ノードの生成
                step_functions = []
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
                    code_lines.append(f"    params = {dep_var}_module.Input(")
                    if params_init_str:
                        code_lines.append(params_init_str)
                    code_lines.append("    )")
                    
                    code_lines.append(f"    res_str = {dep_var}_module.process_message(params, tool_context)")
                    code_lines.append("    try:")
                    code_lines.append("        res_data = json.loads(res_str)")
                    code_lines.append("        tool_context.state.update(res_data)")
                    code_lines.append("    except Exception:")
                    code_lines.append("        pass")
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
            except Exception as e:
                print(f"エラー: workflow.py の LLM 生成または組み立てに失敗しました。プレースホルダーにフォールバックします: {e}")
                workflow_tmpl = self.coder_skill.load_asset("templates/workflow/workflow.py.template")
                workflow_code = workflow_tmpl.replace("{workflow_name}", workflow_name).replace("{workflow_module_name}", workflow_module_name)
        else:
            workflow_tmpl = self.coder_skill.load_asset("templates/workflow/workflow.py.template")
            workflow_code = workflow_tmpl.replace("{workflow_name}", workflow_name).replace("{workflow_module_name}", workflow_module_name)

        with open(workflow_path, "w", encoding="utf-8") as f:
            f.write(workflow_code)
        print(f"workflow.py を生成しました: {workflow_path}")
        generated_files.append(os.path.relpath(workflow_path, self.target_root_dir))

        # 5. workflow_logic.py のプレースホルダー配置（存在しない場合のみ）
        logic_path = os.path.join(self.scripts_dir, "workflow_logic.py")
        if not os.path.exists(logic_path):
            logic_tmpl = self.coder_skill.load_asset("templates/workflow/workflow_logic.py.template")
            logic_code = logic_tmpl.replace("{workflow_name}", workflow_name)
            with open(logic_path, "w", encoding="utf-8") as f:
                f.write(logic_code)
            print(f"workflow_logic.py のプレースホルダーを配置しました: {logic_path}")
            generated_files.append(os.path.relpath(logic_path, self.target_root_dir))

        return generated_files


class CodeGenerator:
    """
    スキルまたはワークフローの実装に必要なコードファイルを
    決定論的に自動生成するファクトリラッッパークラス。
    """
    def __init__(self, 
                 design: SkillDesign, 
                 target_root_dir: str, 
                 coder_skill: Skill):
        # module_type に応じて適切なジェネレータを選択
        if design.module_type == ModuleType.WORKFLOW:
            self._generator = WorkflowAgentCodeGenerator(design, target_root_dir, coder_skill)
        else:
            self._generator = ToolSkillCodeGenerator(design, target_root_dir, coder_skill)

    def generate_all(self) -> List[str]:
        """
        すべての決定論的ファイルを生成します。
        生成されたファイルの相対パスリストを返します。
        """
        return self._generator.generate()
