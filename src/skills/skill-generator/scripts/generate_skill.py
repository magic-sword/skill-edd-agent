"""
ADKのサブエージェント（SkillDeveloperAgent）を動的に起動し、
指定された要件に基づくスキル（SKILL.md, scripts/*.py, tests/*.json）の生成と、
スクリプトが正常にエラーなく動作することの自律検証を行うスクリプト。
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

# インポートキャッシュの不整合対策
sys.modules.pop('google', None)
sys.modules.pop('google.adk', None)

async def run_skill_developer_agent(output_dir: str, prompt: str, model: str, max_turns: int):
    # パス情報の解析
    output_dir = os.path.abspath(output_dir)
    skill_name = os.path.basename(output_dir)
    script_name = skill_name.replace("-", "_") + ".py"
    test_name = skill_name.replace("-", "_") + "_eval_set.evalset.json"
    
    # 開発者エージェントのインストラクション構成
    instruction = (
        f"あなたは Google ADK 2.0 に準拠したスキルを自律開発する、極めて優秀なコーディングエージェント（SkillDeveloperAgent）です。\n"
        f"ユーザーから提示された要件を満たす高品質なスキルアセットを、指定された出力ディレクトリ内に生成してください。\n"
        f"\n"
        f"【開発対象スキルの情報】\n"
        f"- スキル名: {skill_name}\n"
        f"- 出力ディレクトリ: {output_dir}\n"
        f"\n"
        f"【開発ルール（コンテキスト汚染防止・ADKツールスキーマ整合）】\n"
        f"1. 入出力のファイルカプセル化:\n"
        f"   - スキルの実動スクリプトは、大量 of データや状態の受け渡しによる会話のコンテキスト汚染を防ぐため、必ず入力を引数 `--input_json`（ファイルパス）で受け取り、実行結果を引数 `--output_json`（ファイルパス）へJSONファイルとして出力する仕様にしてください。\n"
        f"2. SKILL.md でのツール実行仕様の定義:\n"
        f"   - `SKILL.md` の中の使用手順には、ADKの `run_skill_script` ツールを用いてこのスキルを呼び出す際の、具体的な `args` の JSON 引数構造（キーと値の例）を必ず記載してください。\n"
        f"\n"
        f"【作成すべきファイル構成】\n"
        f"1. `SKILL.md`: スキルの仕様・トリガー条件書。以下のフロントマターを先頭に必ず含むこと（日本語で詳細を記述してください）：\n"
        f"   ---\n"
        f"   name: {skill_name}\n"
        f"   description: スキルの短い説明（日本語）\n"
        f"   ---\n"
        f"   ※ 'AIエージェント向け使用方法 (run_skill_script)' というセクションを末尾に作り、`run_skill_script` で実行する際の具体的な `args` のJSON定義例を必ず含めてください。\n"
        f"2. `scripts/{script_name}`: 実際に動くPythonプログラム。引数（`--input_json` と `--output_json`）を解析してJSONファイルを入出力する実動コード。\n"
        f"3. `tests/{test_name}`: 評価用データセット（JSON形式）。eval_set_id, name, eval_cases（eval_id, conversation [invocation_id, user_content, final_response], session_input）を含むこと。"
    )
    
    # エージェント定義
    developer_agent = Agent(
        model=model,
        name='SkillDeveloperAgent',
        instruction=instruction,
        tools=[
            EnvironmentToolset(environment=LocalEnvironment())
        ]
    )
    
    session_id = str(uuid.uuid4())
    print(f"開発者エージェントを起動中... (セッションID: {session_id})")
    
    # 一時フォルダの作成保証
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "tests"), exist_ok=True)
    
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
            parts=[types.Part(text=f"以下の要件に従って、スキルを開発し、スクリプトの動作検証（不具合チェック）を行ってください：\n{prompt}")]
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
