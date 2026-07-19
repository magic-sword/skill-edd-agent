import os
import shutil
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state

def run_finalize_assets_step(tool_context: ToolContext) -> str:
    """
    自律開発された成果物アセット（design.json や SKILL.md など）の最終同期を行い、
    SkillsStateの自動パス解決で発生した重複フォルダをクリーンアップします。
    """
    skill_name = tool_context.state.get("skill")
    output_dir = tool_context.state.get("output_dir")

    if not skill_name or not output_dir:
        print("[skill-developer] Skip finalization: 'skill' or 'output_dir' is not specified.")
        return "Skip finalization: output_dir not specified."

    output_dir = os.path.abspath(output_dir)
    print(f"[skill-developer] 成果物アセットの最終同期とクリーンアップを開始します (target={output_dir})...")

    try:
        state = SkillsState()
        # 動的スキャンを実行して、現在の登録パスを特定
        state.scan_skills(force_reload=True)
        skill_obj = state.get_skill(skill_name)
        resolved_root = os.path.abspath(skill_obj.root_dir)

        # もし解決された物理フォルダと、明示指定された出力フォルダが乖離している場合
        if resolved_root != output_dir:
            print(f"[skill-developer] 乖離を検出しました: {resolved_root} (SkillsState) != {output_dir} (output_dir)")
            
            # design.json や SKILL.md を救出して target 側へコピー
            src_assets_dir = os.path.join(resolved_root, "assets")
            target_assets_dir = os.path.join(output_dir, "assets")
            
            # design.json
            src_design = os.path.join(src_assets_dir, "design.json")
            if os.path.exists(src_design):
                os.makedirs(target_assets_dir, exist_ok=True)
                shutil.copy2(src_design, os.path.join(target_assets_dir, "design.json"))
                print(f"[skill-developer] ℹ️ design.json を {resolved_root} から {output_dir} へ再配置しました。")

            # SKILL.md
            src_spec = os.path.join(resolved_root, "SKILL.md")
            if os.path.exists(src_spec):
                shutil.copy2(src_spec, os.path.join(output_dir, "SKILL.md"))
                print(f"[skill-developer] ℹ️ SKILL.md を {resolved_root} から {output_dir} へ再配置しました。")

            # 不要になった重複ディレクトリ（src/skills 配下の誤作動フォルダなど）を削除
            shutil.rmtree(resolved_root)
            print(f"[skill-developer] ℹ️ 重複した一時フォルダ '{resolved_root}' を完全にクリーンアップしました。")

        # 正常に終了
        result = {
            "status": "success",
            "message": "成果物アセットの同期とクリーンアップが正常に完了しました。"
        }
        return merge_result_to_state(tool_context, result)

    except Exception as e:
        print(f"[skill-developer] Warning: Failed to finalize assets: {e}")
        # 後処理の失敗でワークフロー全体をエラーにしないため、警告ログに留めて成功を返します。
        return f"Finalization finished with warning: {e}"
