import os
import json
import asyncio
from google.adk.tools import ToolContext
from edd_agent_tools.registry import SkillRegistry
from edd_agent_tools.models import SkillDesign
from .models import Input, Output
from .code_generator import CodeGenerator
from .agent_executor import SkillDeveloperAgentExecutor

def process_message(params: Input, tool_context: ToolContext) -> Output:
    """
    skill-coder のメインビジネスロジック。
    - design.json をロードし、scripts/handler.py を決定論的に自動生成。
    - SkillDeveloperAgent を起動して、オブジェクト指向で分割されたビジネスロジックコード（logic.py等）を段階的にコーディング。
    """
    prompt = params.prompt
    skill = params.skill
    design_path = params.design_path
    output_dir = params.output_dir
    
    if not prompt:
        raise ValueError("必須パラメータ 'prompt' が指定されていません。")
    if not skill and not design_path:
        raise ValueError("対象スキルを特定するために、'skill' または 'design_path' のいずれか一方は必ず指定する必要があります。")
        
    registry = SkillRegistry()
    
    design_path_fallback = os.path.abspath(design_path) if design_path else None
    directory = registry.get_skill_directory(name=skill, design_path=design_path_fallback)
    
    skill_name = directory.name
    target_root = os.path.abspath(output_dir or directory.root_dir)

    # 1. design.json のロード
    design_data: SkillDesign = directory.load_design()
    design_json_str = json.dumps(design_data.model_dump(), indent=2, ensure_ascii=False)
    
    # 2. 決定論的コードの生成（models.py, handler.py, __init__.py, logic.pyプレースホルダー）
    coder_directory = registry.get_skill_directory(name="skill-coder")
    code_generator = CodeGenerator(design=design_data, 
                                   target_root_dir=target_root, 
                                   coder_directory=coder_directory)
    generated_files_by_generator = code_generator.generate_all()
            
    # 3. SkillDeveloperAgent の起動とコーディング実行
    agent_executor = SkillDeveloperAgentExecutor(skill_name=skill_name,
                                                 prompt=prompt,
                                                 target_root_dir=target_root,
                                                 coder_directory=coder_directory)
    generated_files_by_agent = asyncio.run(agent_executor.execute(design_json_str))
    
    # 生成されたファイルを統合
    all_generated_files = list(set(generated_files_by_generator + generated_files_by_agent))
    all_generated_files.sort()

    message = f"スキルコードの実装が完了しました。生成/更新ファイル: {', '.join(all_generated_files)}"
    
    return Output(status="success", generated_files=all_generated_files, result_message=message)
