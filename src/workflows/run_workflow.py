"""
ADK 2.0 Workflow の実行を行う共通の起動スクリプト。
指定されたワークフローフォルダの SKILL.md に定義された dependencies をチェックし、
問題がなければ workflow.py から Workflow オブジェクトを動的にロードして実行します。
"""
import argparse
import asyncio
import os
import sys
import json
import uuid
import yaml
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types

def parse_dependencies_from_skill_md(workflow_name: str) -> list[str]:
    """
    src/workflows/{workflow_name}/SKILL.md から YAML フロントマターを読み込み、
    dependencies を抽出します。
    """
    skill_md_path = os.path.abspath(f"/workspace/src/workflows/{workflow_name}/SKILL.md")
    if not os.path.exists(skill_md_path):
        print(f"警告: SKILL.md が見つかりません: {skill_md_path}")
        return []
        
    try:
        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # YAMLフロントマターを抽出する簡易パーサー
        # 最初の "---" と次の "---" の間を取り出す
        parts = content.split("---")
        if len(parts) >= 3:
            yaml_content = parts[1]
            data = yaml.safe_load(yaml_content)
            if isinstance(data, dict):
                return data.get("dependencies", [])
    except Exception as e:
        print(f"エラー: SKILL.md から依存関係を解析できませんでした: {e}", file=sys.stderr)
        
    return []

def validate_dependencies(workflow_name: str, dependencies: list[str]):
    """
    依存関係の検証。
    1. registry_path (/workspace/src/skills_registry.json) に登録されていること
    2. src/skills/{dependency} フォルダが実際に存在していること
    """
    if not dependencies:
        return
        
    print(f"🔍 依存関係チェック中: {workflow_name}")
    
    registry_path = "/workspace/src/skills_registry.json"
    skills_registry = {}
    if os.path.exists(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                skills_registry = data.get("skills", {})
        except Exception as e:
            print(f"警告: skills_registry.json の読み込みに失敗しました: {e}", file=sys.stderr)
            
    missing_in_registry = []
    missing_dir = []
    
    for dep in dependencies:
        # registry に登録されているか確認
        if dep not in skills_registry:
            missing_in_registry.append(dep)
            
        # フォルダが存在するか確認
        dep_dir = os.path.abspath(f"/workspace/src/skills/{dep}")
        if not os.path.isdir(dep_dir):
            missing_dir.append(dep)
            
    if missing_in_registry or missing_dir:
        err_msg = (
            f"【依存関係エラー】ワークフロー '{workflow_name}' の実行に必要なスキルが不足しています:\n"
        )
        if missing_in_registry:
            err_msg += f"    レジストリ未登録: {', '.join(missing_in_registry)}\n"
        if missing_dir:
            err_msg += f"    ディレクトリ未存在: {', '.join(missing_dir)}\n"
        err_msg += f"    依存スキル一覧: {dependencies}"
        raise RuntimeError(err_msg)
        
    print(f"✅ 依存関係チェック通過: {dependencies}")

async def main():
    parser = argparse.ArgumentParser(description="Google ADK 2.0 共通ワークフロー実行エントリーポイント")
    parser.add_argument("--workflow_name", default="generate-skill-workflow", help="実行するワークフロー名")
    parser.add_argument("--skill_name", help="作成・評価するスキルの名前")
    parser.add_argument("--prompt", help="スキルの仕様や要件プロンプト")
    parser.add_argument("--input_json", help="入力パラメータ用JSONファイルのパス")
    parser.add_argument("--output_json", help="結果出力用JSONファイルのパス")
    
    args = parser.parse_args()
    
    workflow_name = args.workflow_name
    skill_name = args.skill_name
    prompt = args.prompt
    
    if args.input_json:
        try:
            with open(args.input_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                workflow_name = data.get("workflow_name", workflow_name)
                skill_name = data.get("skill_name", skill_name)
                prompt = data.get("prompt", prompt)
        except Exception as e:
            print(f"Error reading input_json: {e}", file=sys.stderr)
            sys.exit(1)
            
    if not skill_name or not prompt:
        print("エラー: --skill_name と --prompt、もしくは --input_json は必須です。", file=sys.stderr)
        sys.exit(1)
        
    # 1. 依存関係のロードとチェック
    dependencies = parse_dependencies_from_skill_md(workflow_name)
    try:
        validate_dependencies(workflow_name, dependencies)
    except RuntimeError as e:
        print(f"エラー: {e}", file=sys.stderr)
        if args.output_json:
            try:
                with open(args.output_json, "w", encoding="utf-8") as f:
                    json.dump({
                        "status": "failed",
                        "message": str(e),
                        "skill_name": skill_name
                    }, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
        sys.exit(1)
        
    # 2. ワークフローモジュールの動的インポート
    print(f"📦 ワークフローをロード中: {workflow_name}")
    workflow_script_dir = os.path.abspath(f"/workspace/src/workflows/{workflow_name}/scripts")
    if not os.path.exists(workflow_script_dir):
        print(f"エラー: ワークフロールートが見つかりません: {workflow_script_dir}", file=sys.stderr)
        sys.exit(1)
        
    # 動的インポートのために sys.path を変更する
    if workflow_script_dir not in sys.path:
        sys.path.insert(0, workflow_script_dir)
        
    try:
        import workflow
        root_workflow = workflow.root_workflow
    except Exception as e:
        print(f"エラー: ワークフロー '{workflow_name}' のロードに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)
        
    print(f"==================================================")
    print(f"DAGワークフロー実行起動: {workflow_name}")
    print(f"==================================================")
    
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    
    session_id = str(uuid.uuid4())
    
    # 起動前にセッションを作成し、共有セッション状態 (Session State) を初期化
    session = await session_service.create_session(
        user_id="workflow_user",
        session_id=session_id,
        app_name=f"{workflow_name}_runner"
    )
    session.state["temp:skill_name"] = skill_name
    session.state["temp:prompt"] = prompt
    session.state["temp:registry_path"] = "/workspace/src/skills_registry.json"
    session.state["temp:status"] = "success"
    session.state["temp:message"] = "Workflow successfully completed."
    
    status = "success"
    message = "Workflow successfully completed."
    
    async with Runner(
        app_name=f"{workflow_name}_runner",
        agent=root_workflow,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        # 最初の起動トリガーメッセージ
        user_message = types.Content(
            role='user',
            parts=[types.Part(text="スキル開発ワークフローを開始してください。")]
        )
        
        try:
            async for event in runner.run_async(
                user_id="workflow_user",
                session_id=session_id,
                new_message=user_message,
            ):
                # ログの出力があれば表示
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(part.text)
                            
            # 完了後、セッション状態から最終結果を取得
            final_session = await session_service.get_session(user_id="workflow_user", session_id=session_id)
            if final_session and "temp:status" in final_session.state:
                status = final_session.state["temp:status"]
                message = final_session.state.get("temp:message", message)
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
