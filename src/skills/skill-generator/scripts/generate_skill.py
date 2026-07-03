"""
ADKのサブエージェント（SkillDeveloperAgent）を動的に起動し、
指定された要件に基づくスキル（SKILL.md, scripts/*.py）のコード実装を行うスクリプト。
"""
import argparse
import asyncio
import json
import os
import sys
import uuid
from google.adk import Agent
from google.adk.environment import LocalEnvironment
from google.adk.tools.environment import EnvironmentToolset
from google.adk.runners import Runner
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from google.adk.tools import ToolContext
from google.adk.tools.environment._read_file_tool import ReadFileTool
from google.adk.tools.environment._edit_file_tool import EditFileTool
from google.adk.tools.environment._write_file_tool import WriteFileTool
from edd_agent_tools.testing import LibraryDocumentationReader


# インポートキャッシュの不整合対策
sys.modules.pop('google', None)
sys.modules.pop('google.adk', None)

async def run_skill_developer_agent(output_dir: str, prompt: str, model: str, max_turns: int):
    # パス情報の解析
    output_dir = os.path.abspath(output_dir)
    skill_name = os.path.basename(output_dir)
    script_name = skill_name.replace("-", "_") + ".py"
    
    # テンプレートおよびプロンプトアセットの読み込み
    generator_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(generator_dir, "..", "assets")
    
    inst_path = os.path.join(assets_dir, "system_instruction.txt")
    if not os.path.exists(inst_path):
        raise FileNotFoundError(f"Error: Instruction file {inst_path} not found.")
        
    with open(inst_path, "r", encoding="utf-8") as f:
        instruction_template = f.read()
        
    instruction = instruction_template.replace(
        "{skill_name}", skill_name
    ).replace(
        "{output_dir}", output_dir
    ).replace(
        "{script_name}", script_name
    )
    
    # 共通ライブラリ（edd-agent-tools）の公式仕様書を提供する動的リーダーツールを初期化
    reader = LibraryDocumentationReader(library_name="edd_agent_tools")
    
    # エージェント定義
    local_env = LocalEnvironment(working_dir=output_dir)
    developer_agent = Agent(
        model=model,
        name='SkillDeveloperAgent',
        instruction=instruction,
        tools=[
            ReadFileTool(local_env),
            EditFileTool(local_env),
            WriteFileTool(local_env),
            reader.read_documentation, # インスタンスのバインドされたメソッドをそのまま手渡す
        ]
    )
    
    session_id = str(uuid.uuid4())
    print(f"開発者エージェントを起動中... (セッションID: {session_id})")
    
    # 一時フォルダの作成保証
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "references"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "assets"), exist_ok=True)

    # テンプレートファイルをコピー・展開
    generator_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(generator_dir, "..", "assets")
    
    skill_md_tmpl_path = os.path.join(templates_dir, "SKILL.md.template")
    skill_script_tmpl_path = os.path.join(templates_dir, "skill_script.py.template")
    
    if os.path.exists(skill_md_tmpl_path):
        with open(skill_md_tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
        content = tmpl_content.replace("{skill_name}", skill_name).replace("{skill_description}", prompt).replace("{script_name}", script_name)
        with open(os.path.join(output_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(content)
            
    if os.path.exists(skill_script_tmpl_path):
        with open(skill_script_tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
        with open(os.path.join(output_dir, "scripts", script_name), "w", encoding="utf-8") as f:
            f.write(tmpl_content)
    
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    
    async with Runner(
        app_name="skill_generator_runner",
        agent=developer_agent,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        user_message = types.Content(
            role='user',
            parts=[types.Part(text=f"以下の要件に従って、対象スキルのビジネスロジックを実装してください：\n{prompt}")]
        )
        
        # サブエージェントの推論を実行し、進行状況をコンソールに出力
        async for event in runner.run_async(
            user_id="skill_generator",
            session_id=session_id,
            new_message=user_message,
        ):
            author = event.author or "Agent"
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{author}]: {part.text}")
                    if part.function_call:
                        fc = part.function_call
                        print(f"[{author} ツール実行]: {fc.name}({fc.args})")

async def generate_skill_code(tool_context: ToolContext) -> str:
    """
    指定された要件（prompt）に基づき、SkillDeveloperAgent を起動して
    新規スキルを自律生成します。
    """
    skill_name = tool_context.state.get("skill_name")
    prompt = tool_context.state.get("prompt")
    
    if not skill_name or not prompt:
        raise ValueError("セッション状態に 'skill_name' または 'prompt' が設定されていません。")
        
    output_dir = os.path.abspath(f"/workspace/src/skills/{skill_name}")
    model = "gemini-2.5-flash"
    max_turns = 15
    
    # 開発者エージェントを実行
    await run_skill_developer_agent(
        output_dir=output_dir,
        prompt=prompt,
        model=model,
        max_turns=max_turns
    )
    
    # スキル仕様書（SKILL.md）が作成されたことを確認
    skill_md_path = os.path.join(output_dir, "SKILL.md")
    if not os.path.exists(skill_md_path):
        raise ValueError(f"Skill specification 'SKILL.md' was not generated at {skill_md_path}.")
        
    output_json_path = f"/workspace/src/.workflow_tmp/{skill_name}/02_gen_out.json"
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": "success",
            "message": "Successfully generated skill.",
            "output_dir": output_dir
        }, f, indent=2, ensure_ascii=False)
        
    tool_context.state["skill_dir"] = output_dir
    
    return f"Success: Generated skill '{skill_name}' at '{output_dir}'."


def main():
    parser = argparse.ArgumentParser(description="ADKサブエージェントを用いたスキルの自律的生成と検証")
    parser.add_argument("--output_dir", required=True, help="スキルの出力先 (例: src/skills/my-skill)")
    parser.add_argument("--prompt", required=True, help="生成したいスキルの説明や要件")
    parser.add_argument("--model", default="gemini-2.5-flash", help="使用するモデル名")
    parser.add_argument("--max_attempts", type=int, default=15, help="サブエージェントの最大ターン数")
    parser.add_argument("--output_json", help="Path to output JSON file")
    
    args = parser.parse_args()
    
    if not os.environ.get("GEMINI_API_KEY"):
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。", file=sys.stderr)
        sys.exit(1)
        
    status = "success"
    message = "Successfully generated skill."
    output_dir = os.path.abspath(args.output_dir)
    
    print(f"=== スキル開発タスクを開始します ===")
    print(f"出力先: {output_dir}")
    print(f"要件: {args.prompt}")
    
    try:
        asyncio.run(
            run_skill_developer_agent(
                output_dir=output_dir,
                prompt=args.prompt,
                model=args.model,
                max_turns=args.max_attempts
            )
        )
        print("\n=== スキル開発タスクが完了しました ===")
    except Exception as e:
        status = "failed"
        message = str(e)
        print(f"Error: {e}", file=sys.stderr)
        
    if args.output_json:
        try:
            out_dir = os.path.dirname(os.path.abspath(args.output_json))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.output_json, "w", encoding="utf-8") as f:
                json.dump({
                    "status": status,
                    "message": message,
                    "output_dir": output_dir
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing output_json: {e}", file=sys.stderr)
            
    if status == "failed":
        sys.exit(1)

if __name__ == "__main__":
    main()
