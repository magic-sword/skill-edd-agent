"""
ADK 2.0 Workflow の実行を行う薄い起動スクリプト。
"""
import argparse
import asyncio
import os
import sys
import json
import uuid
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types
from workflows.generate_skill_workflow import root_workflow

async def main():
    parser = argparse.ArgumentParser(description="Google ADK 2.0 ワークフロー実行エントリーポイント")
    parser.add_argument("--skill_name", help="作成・評価するスキルの名前")
    parser.add_argument("--prompt", help="スキルの仕様や要件プロンプト")
    parser.add_argument("--input_json", help="入力パラメータ用JSONファイルのパス")
    parser.add_argument("--output_json", help="結果出力用JSONファイルのパス")
    
    args = parser.parse_args()
    
    skill_name = args.skill_name
    prompt = args.prompt
    
    if args.input_json:
        try:
            with open(args.input_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                skill_name = data.get("skill_name", skill_name)
                prompt = data.get("prompt", prompt)
        except Exception as e:
            print(f"Error reading input_json: {e}", file=sys.stderr)
            sys.exit(1)
            
    if not skill_name or not prompt:
        print("エラー: --skill_name と --prompt、もしくは --input_json は必須です。", file=sys.stderr)
        sys.exit(1)
        
    print(f"==================================================")
    print(f"DAGワークフロー実行起動: {skill_name}")
    print(f"==================================================")
    
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    
    status = "success"
    message = "Workflow successfully completed."
    
    async with Runner(
        app_name="generate_skill_workflow_runner",
        agent=root_workflow,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        # パラメータを JSON 文字列にして 1つの node_input として渡す
        input_data = json.dumps({
            "skill_name": skill_name,
            "prompt": prompt
        })
        
        user_message = types.Content(
            role='user',
            parts=[types.Part(text=input_data)]
        )
        
        session_id = str(uuid.uuid4())
        
        try:
            async for event in runner.run_async(
                user_id="workflow_user",
                session_id=session_id,
                new_message=user_message,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            # 最終的な戻り値JSONを解析
                            try:
                                result = json.loads(part.text)
                                if "status" in result:
                                    status = result["status"]
                                    message = result.get("message", message)
                            except Exception:
                                pass
        except Exception as e:
            status = "failed"
            message = str(e)
            
    print(f"\n==================================================")
    print(f"DAGワークフロー実行終了: {status}")
    print(f"メッセージ: {message}")
    print(f"==================================================")
    
    if args.output_json:
        try:
            out_dir = os.path.dirname(os.path.abspath(args.output_json))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.output_json, "w", encoding="utf-8") as f:
                json.dump({
                    "status": status,
                    "message": message,
                    "skill_name": skill_name
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing output_json: {e}", file=sys.stderr)
            
    if status == "failed":
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
