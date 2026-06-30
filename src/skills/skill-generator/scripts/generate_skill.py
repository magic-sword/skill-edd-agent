"""
ユーザーの要望に応じて、Google ADK 2.0 互換のスキル（SKILL.md, scripts/*.py, tests/*.evalset.json）を
自律的かつ評価駆動（自己修復ループ付き）で生成するスクリプト。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError

# インポートキャッシュの不整合対策（ADK eval用）
sys.modules.pop('google', None)
sys.modules.pop('google.adk', None)

class SkillAsset(BaseModel):
    filename: str = Field(description="ファイル名（例: README.md または config.json）")
    content: str = Field(description="ファイルの内容")

class SkillGenerationResult(BaseModel):
    skill_name: str = Field(description="生成するスキルの名前（ケバブケース、例: text-summarizer）")
    skill_md: str = Field(description="SKILL.md の中身。YAMLフロントマター（name, description）を必ず含むこと。")
    script_name: str = Field(description="scripts/ ディレクトリに配置するスクリプトファイル名（スネークケース、例: summarize.py）")
    script_content: str = Field(description="実行されるPythonスクリプトの完全なコード。引数を解析し、必要な処理を実行して結果を出力すること。日本語のドキュメントやコメントを含むこと。")
    test_name: str = Field(description="tests/ ディレクトリに配置するテストファイル名（例: summarize_eval_set.evalset.json）")
    test_content: str = Field(description="AgentEvaluator用のテストデータセットのJSON文字列。eval_set_id, name, eval_cases（eval_id, conversation [invocation_id, user_content, final_response], session_input）を含むこと。")
    references: list[SkillAsset] = Field(default=[], description="references/ ディレクトリに配置する参考資料アセット。")
    assets: list[SkillAsset] = Field(default=[], description="assets/ ディレクトリに配置するアセットファイル。")

# Gemini APIに与えるシステム指示書を assets/ から読み込む
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "assets")
SYSTEM_INSTRUCTION_PATH = os.path.join(ASSETS_DIR, "system_instruction.txt")

if not os.path.exists(SYSTEM_INSTRUCTION_PATH):
    raise FileNotFoundError(f"システム指示書アセットが見つかりません: {SYSTEM_INSTRUCTION_PATH}")

with open(SYSTEM_INSTRUCTION_PATH, "r", encoding="utf-8") as f:
    SYSTEM_INSTRUCTION = f.read()

def generate_skill_assets(client: genai.Client, model: str, prompt: str, error_feedback: str = None) -> SkillGenerationResult:
    """Gemini API を呼び出してスキルアセットを生成します。"""
    contents = [f"以下の要件を満たすスキルを生成してください:\n{prompt}"]
    if error_feedback:
        contents.append(f"\n--- 前回の生成で以下のテストエラーが発生しました。これを修正した完全なコードを再生成してください ---\n{error_feedback}")
    
    print(f"Gemini API ({model}) を呼び出し中...")
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SkillGenerationResult,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
        )
    )
    # JSON文字列からPydanticオブジェクトへロード
    return SkillGenerationResult.model_validate_json(response.text)

def backup_agent_py(agent_py_path: str) -> str:
    """agent.py のバックアップを作成します。"""
    backup_path = f"{agent_py_path}.bak"
    shutil.copyfile(agent_py_path, backup_path)
    return backup_path

def restore_agent_py(agent_py_path: str, backup_path: str):
    """agent.py をバックアップから復元します。"""
    if os.path.exists(backup_path):
        shutil.copyfile(backup_path, agent_py_path)
        os.remove(backup_path)

def integrate_skill_into_agent_py(agent_py_path: str, skill_name: str, skill_var_name: str):
    """agent.py を一時的に書き換え、新しいスキルをロードするように追加します。"""
    with open(agent_py_path, "r", encoding="utf-8") as f:
        content = f.read()

    # スキルロード部分の定義を作成
    # 既存の skill_generator_skill ロード処理の直後に追加する
    load_pattern = r"(skill_generator_skill = load_skill_from_dir\([\s\S]*?\))"
    new_load_code = f"\n\n# 自動生成されたスキルのロード\n{skill_var_name} = load_skill_from_dir(\n    current_dir / \"skills\" / \"{skill_name}\"\n)"
    
    if re.search(load_pattern, content):
        content = re.sub(load_pattern, rf"\1{new_load_code}", content)
    else:
        # 見つからない場合は import の後あたりに適当に追加
        content = content.replace("current_dir = pathlib.Path(__file__).parent", f"current_dir = pathlib.Path(__file__).parent{new_load_code}")

    # SkillToolset へのスキル追加
    # skills=[skill_generator_skill] -> skills=[skill_generator_skill, new_skill]
    # 複数行や他の引数（code_executorなど）があっても正しくマッチするように定義
    toolset_pattern = r"(skill_toolset\.SkillToolset\(\s*skills=\[)([\s\S]*?)(\])"
    def replace_skills(match):
        prefix = match.group(1)
        existing_skills = match.group(2).strip()
        suffix = match.group(3)
        if existing_skills:
            return f"{prefix}{existing_skills}, {skill_var_name}{suffix}"
        else:
            return f"{prefix}{skill_var_name}{suffix}"
    
    content = re.sub(toolset_pattern, replace_skills, content)

    with open(agent_py_path, "w", encoding="utf-8") as f:
        f.write(content)

def run_adk_eval(test_file_path: str) -> tuple[bool, str]:
    """adk eval run をサブプロセスで実行し、結果を返します。"""
    venv_python = "/workspace/.venv/bin/python"
    eval_command = [
        venv_python, "-m", "google.adk.cli.cli", "eval", "run",
        "/workspace/src",
        test_file_path
    ]
    print(f"テスト検証を実行中: {' '.join(eval_command)}")
    result = subprocess.run(eval_command, capture_output=True, text=True)
    
    success = result.returncode == 0
    output = result.stdout + "\n" + result.stderr
    return success, output

def load_directory_contents_for_prompt(dir_path: str) -> str:
    """指定されたディレクトリ内のテキストファイルの中身を再帰的にスキャンして返します。"""
    if not dir_path or not os.path.exists(dir_path):
        return ""
    result = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, dir_path)
            # テキスト系の拡張子のみ読み取る
            if file.endswith((".txt", ".json", ".md", ".yaml", ".yml", ".csv", ".py")):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    result.append(f"--- ファイル: {rel_path} ---\n{content}\n")
                except Exception:
                    pass
    return "\n".join(result)


def main():
    parser = argparse.ArgumentParser(description="A2A互換スキルの自律的生成および評価駆動型デバッグ")
    parser.add_argument("--output_dir", required=True, help="スキルの最終出力先ディレクトリ (例: src/skills/my-skill)")
    parser.add_argument("--prompt", required=True, help="生成したいスキルの説明や要件")
    parser.add_argument("--model", default="gemini-2.5-flash", help="使用するGeminiモデル名")
    parser.add_argument("--max_attempts", type=int, default=3, help="自己修復ループの最大試行回数")
    parser.add_argument("--ref_assets_dir", help="生成先スキルディレクトリへ事前にコピーし、AIへ参考コンテキストとして渡すディレクトリのパス（任意）")
    
    args = parser.parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    # パスの定義
    output_dir = os.path.abspath(args.output_dir)
    skill_name = os.path.basename(output_dir)
    skill_var_name = skill_name.replace("-", "_") + "_skill"
    
    agent_py_path = "/workspace/src/agent.py"
    backup_path = None
    
    # 出力先ディレクトリの親が存在するか確認
    os.makedirs(os.path.dirname(output_dir), exist_ok=True)
    
    error_feedback = None
    success = False
    
    for attempt in range(1, args.max_attempts + 1):
        print(f"\n=== スキル生成 試行 {attempt}/{args.max_attempts} ===")
        
        try:
            # 1. スキルの生成
            # ユーザーが指定した事前アセットについての情報と、その「ファイルの中身（コンテンツ）」をプロンプトに注入する
            enhanced_prompt = args.prompt
            if args.ref_assets_dir:
                ref_assets_content = load_directory_contents_for_prompt(args.ref_assets_dir)
                if ref_assets_content:
                    enhanced_prompt += f"\n\n※ スキルディレクトリには、すでに以下の参考ファイルが配置されています。PythonスクリプトやSKILL.md、評価データセットはこれらが存在する前提で実装・定義し、参照・利用・補完してください：\n{ref_assets_content}"
            
            assets = generate_skill_assets(client, args.model, enhanced_prompt, error_feedback)
            
            # 2. 一時的なファイル書き出し
            # テストファイルは tests/ の下に配置
            test_file_path = os.path.join("/workspace/tests", assets.test_name)
            
            # スキルフォルダのクリーンアップと再作成
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(os.path.join(output_dir, "scripts"), exist_ok=True)
            os.makedirs(os.path.join(output_dir, "references"), exist_ok=True)
            os.makedirs(os.path.join(output_dir, "assets"), exist_ok=True)
            
            # 事前アセットの丸ごとコピー
            copied_files = []
            if args.ref_assets_dir and os.path.exists(args.ref_assets_dir):
                shutil.copytree(args.ref_assets_dir, output_dir, dirs_exist_ok=True)
                for root, _, files in os.walk(args.ref_assets_dir):
                    for file in files:
                        copied_files.append(file)
            
            # 各ファイルの保存 (すでにコピー済みのファイルが存在しない場合のみ書き出す)
            if "SKILL.md" not in copied_files:
                with open(os.path.join(output_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                    f.write(assets.skill_md)
                
            script_path = os.path.join(output_dir, "scripts", assets.script_name)
            if assets.script_name not in copied_files:
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(assets.script_content)
                # スクリプトに実行権限を付与
                os.chmod(script_path, 0o755)
            
            # references/ ディレクトリへ書き出し
            for ref in getattr(assets, "references", []):
                if ref.filename not in copied_files:
                    ref_path = os.path.join(output_dir, "references", ref.filename)
                    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
                    with open(ref_path, "w", encoding="utf-8") as f:
                        f.write(ref.content)
                    
            # assets/ ディレクトリへ書き出し
            for asset in getattr(assets, "assets", []):
                if asset.filename not in copied_files:
                    asset_path = os.path.join(output_dir, "assets", asset.filename)
                    os.makedirs(os.path.dirname(asset_path), exist_ok=True)
                    with open(asset_path, "w", encoding="utf-8") as f:
                        f.write(asset.content)
                
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(assets.test_content)
                
            print(f"アセットの書き出し完了: {assets.skill_name}")
            
            # 3. agent.py への一時的なインテグレーション
            backup_path = backup_agent_py(agent_py_path)
            integrate_skill_into_agent_py(agent_py_path, skill_name, skill_var_name)
            
            # 4. テストの実行と評価
            eval_success, eval_output = run_adk_eval(test_file_path)
            print(eval_output)
            
            if eval_success:
                print(f"🎉 試行 {attempt}: テストが正常に通過しました！")
                success = True
                break
            else:
                print(f"⚠️ 試行 {attempt}: テストが失敗しました。エラーログを収集します。")
                error_feedback = eval_output
                
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            error_feedback = str(e)
            
        finally:
            # 失敗した場合は agent.py を復元し、後続の試行に備える
            if backup_path and os.path.exists(backup_path):
                restore_agent_py(agent_py_path, backup_path)
                backup_path = None

    # 最終的な後片付けと報告
    if success:
        print("\n=== スキル生成およびテスト検証が正常に完了しました ===")
        print(f"生成先: {output_dir}")
        # 成功したのでバックアップは削除（統合された状態を維持）
        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)
    else:
        print("\n=== エラー: スキルの生成およびテスト検証に失敗しました ===")
        # 失敗したので agent.py を完全に元に戻す
        if backup_path:
            restore_agent_py(agent_py_path, backup_path)
        # 生成したファイルをクリーンアップ
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        sys.exit(1)

if __name__ == "__main__":
    main()
