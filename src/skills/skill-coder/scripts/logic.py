import os
import json
import asyncio
import subprocess
import uuid
import threading
from concurrent.futures import Future
from typing import List

from edd_agent_tools.skills import SkillsState
from edd_agent_tools import SkillDesign
from .models import SkillCoderOutput
from .code_generator import CodeGenerator
from .agent_executor import SkillDeveloperAgentExecutor

class SkillLogic:
    """
    SkillDeveloperAgent を統制し、アセットおよびモジュールコード生成を実行する
    オブジェクト指向のビジネスロジック。
    """
    def __init__(self, prompt: str, skill: str = None, design_path: str = None, output_dir: str = None):
        self.prompt = prompt
        self.skill = skill
        self.design_path = design_path
        self.output_dir = output_dir
        self.state = SkillsState()

    def execute(self) -> SkillCoderOutput:
        prompt = self.prompt or ""
        skill = self.skill
        design_path = self.design_path
        output_dir = self.output_dir
        
        if not skill and not design_path:
            raise ValueError("対象スキルを特定するために、'skill' または 'design_path' のいずれか一方は必ず指定する必要があります。")
            
        design_path_fallback = os.path.abspath(design_path) if design_path else None
        skill_obj = self.state.get_skill(name=skill, design_path=design_path_fallback)
        
        skill_name = skill_obj.name
        target_root = os.path.abspath(output_dir or skill_obj.root_dir)

        # 1. design.json のロード
        design_data: SkillDesign = skill_obj.load_design()
        design_json_str = json.dumps(design_data.model_dump(), indent=2, ensure_ascii=False)
        
        # 2. 決定論的コードの生成（models.py, handler.py, __init__.py, executor.pyプレースホルダー）
        coder_skill = self.state.get_skill("skill-coder")
        code_generator = CodeGenerator(design=design_data, 
                                       target_root_dir=target_root, 
                                       coder_skill=coder_skill)
        generated_files_by_generator = code_generator.generate_all()
                
        # 3. SkillDeveloperAgent の起動とコーディング実行
        # design.json 内の summary (仕様概要) とユーザーの prompt (実装のこだわり) をマージ
        full_prompt = ""
        if getattr(design_data, "summary", None):
            full_prompt = f"=== 基本仕様概要（What） ===\n{design_data.summary}\n\n"
        full_prompt += f"=== 今回の実装・改修要望（How） ===\n{prompt}"

        agent_executor = SkillDeveloperAgentExecutor(skill_name=skill_name,
                                                     prompt=full_prompt,
                                                     target_root_dir=target_root,
                                                     coder_skill=coder_skill)
        generated_files_by_agent = self._run_safe(agent_executor.execute(design_json_str))
        
        # 生成されたファイルを統合
        all_generated_files = list(set(generated_files_by_generator + generated_files_by_agent))
        all_generated_files.sort()

        message = f"スキルコードの実装が完了しました。生成/更新ファイル: {', '.join(all_generated_files)}"
        return SkillCoderOutput(status="success", message=message, output_dir=target_root)

    def _run_safe(self, coro):
        """アクティブなイベントループが存在する場合はスレッド分離して実行、なければ通常通り asyncio.run を実行します。"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            future = Future()
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result = new_loop.run_until_complete(coro)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                finally:
                    new_loop.close()
            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()
            return future.result()
        else:
            return asyncio.run(coro)
