import os
import uuid
import asyncio
import subprocess
from typing import List

from google.adk.tools import ToolContext
from google.adk import Agent
from google.adk.environment import LocalEnvironment
from google.adk.tools.environment._read_file_tool import ReadFileTool
from edd_agent_tools import SafeWriteFileTool, SafeEditFileTool
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types

from edd_agent_tools.skills import Skill
from edd_agent_tools import LibraryDocumentationReader
from edd_agent_tools.gemini import GeminiRequest

class SkillDeveloperAgentExecutor:
    """
    SkillDeveloperAgent のライフサイクルを管理し、コード生成とコンパイルチェックを実行するクラス。
    """
    def __init__(self,
                 skill_name: str,
                 prompt: str,
                 target_root_dir: str,
                 coder_skill: Skill):
        self._skill_name = skill_name
        self._prompt = prompt
        self._target_root_dir = target_root_dir
        self._scripts_dir = os.path.join(self._target_root_dir, "scripts")
        self._coder_skill = coder_skill

    async def execute(self, design_json_str: str) -> List[str]:
        """
        SkillDeveloperAgent を起動し、コード生成プロセスを実行します。
        生成されたファイルの相対パスリストを返します。
        """
        local_env = LocalEnvironment(working_dir=self._target_root_dir)
        reader = LibraryDocumentationReader(library_name="edd_agent_tools")

        system_instruction_tmpl = self._coder_skill.load_asset("prompts/system_instruction.txt")
        instruction = system_instruction_tmpl.replace(
            "{skill_name}", self._skill_name
        ).replace(
            "{output_dir}", self._target_root_dir
        ).replace(
            "{design_json}", design_json_str
        ).replace(
            "{prompt}", self._prompt
        )

        restricted_files = ["workflow.py", "handler.py", "models.py", "__init__.py", "run_*.py", "design_*.txt", "design_*_template.txt"]
        developer_agent = Agent(
            model="gemini-2.5-flash",
            name='SkillDeveloperAgent',
            instruction=instruction,
            tools=[
                ReadFileTool(local_env),
                SafeEditFileTool(local_env, restricted_patterns=restricted_files),
                SafeWriteFileTool(local_env, restricted_patterns=restricted_files),
                reader.read_documentation
            ]
        )

        session_service = InMemorySessionService()
        artifact_service = InMemoryArtifactService()
        session_id = str(uuid.uuid4())

        user_prompt_tmpl = self._coder_skill.load_asset("prompts/user_prompt.txt")
        user_prompt = user_prompt_tmpl.format(
            skill_name=self._skill_name,
            prompt=self._prompt
        )

        request = GeminiRequest(user_prompt)

        # 既存の scripts ディレクトリ内の全 python ファイル (handler.py 含む) を添付
        if os.path.exists(self._scripts_dir):
            request.add_dir(
                directory=self._scripts_dir,
                ref_root=self._target_root_dir,
                file_filter=lambda p: p.endswith(".py")
            )
            
        docs_content = reader.read_documentation()
        request.add_text(f"=== 開発規約（edd-agent-tools 仕様書） ===\n{docs_content}")

        current_message = types.Content(
            role='user',
            parts=[types.Part(text=p) for p in request.build()]
        )

        generated_files: List[str] = []
        async with Runner(
            app_name="skill_coder_runner",
            agent=developer_agent,
            session_service=session_service,
            artifact_service=artifact_service,
            auto_create_session=True
        ) as runner:
            max_fix_attempts = 3
            for attempt in range(max_fix_attempts + 1):
                async for event in runner.run_async(
                    user_id="skill_coder",
                    session_id=session_id,
                    new_message=current_message,
                ):
                    author = event.author or "Agent"
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                print(f"[{author}]: {part.text}")
                            if part.function_call:
                                fc = part.function_call
                                print(f"[{author} ツール実行]: {fc.name}({fc.args})")

                # コンパイルチェックを実行して生成コードのインポート/構文を検証
                py_files = []
                for r, _, fs in os.walk(self._scripts_dir):
                    for f in fs:
                        if f.endswith(".py"):
                            py_files.append(os.path.join(r, f))
                
                if not py_files:
                    break # 生成されたPythonファイルがない場合はチェックをスキップ

                # py_compile で一括静的チェック
                check_res = subprocess.run(
                    ["python3", "-m", "py_compile"] + py_files,
                    capture_output=True, text=True
                )
                
                if check_res.returncode == 0:
                    print("✅ 生成されたすべての Python ファイルのコンパイルチェックに合格しました。")
                    break
                else:
                    if attempt == max_fix_attempts:
                        print(f"❌ 警告: {max_fix_attempts} 回の自己修復試行後もコンパイルエラーが解消されませんでした。")
                        break
                    
                    print(f"⚠️ コンパイルエラーを検出しました (自己修復試行 {attempt + 1}/{max_fix_attempts}):")
                    print(check_res.stderr)
                    
                    # エラーをフィードバックして再コーディングを要請
                    feedback_prompt = (
                        f"【警告: 生成されたコードにコンパイル/インポートエラーが発生しています】\n"
                        f"以下のエラー内容を確認し、該当ファイルのインポート文やクラス定義・メソッド名を正しく修正してください。\n"
                        f"※正しいモジュール名やインポートパスが使用されているかを確認してください。\n\n"
                        f"エラー内容:\n{check_res.stderr}"
                    )
                    current_message = types.Content(
                        role='user',
                        parts=[types.Part(text=feedback_prompt)]
                    )

        # 生成されたファイルをスキャンして報告
        for root, _, files in os.walk(self._scripts_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self._target_root_dir)
                generated_files.append(rel_path)
                
        assets_dir = os.path.join(self._target_root_dir, "assets")
        if os.path.exists(assets_dir):
            for root, _, files in os.walk(assets_dir):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), self._target_root_dir)
                    generated_files.append(rel_path)
        
        return generated_files
