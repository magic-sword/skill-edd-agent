import os
import shutil
from google.adk.tools import ToolContext

def run_finalize_assets_step(tool_context: ToolContext) -> str:
    generated_assets_path = tool_context.state.get("generated_assets_path")
    output_directory = tool_context.state.get("output_directory")

    if not generated_assets_path:
        tool_context.state["finalization_status"] = "failed"
        return "Error: 'generated_assets_path' not found in tool_context.state. Cannot finalize assets."
    if not output_directory:
        tool_context.state["finalization_status"] = "failed"
        return "Error: 'output_directory' not found in tool_context.state. Cannot finalize assets."

    sync_message = ""
    cleanup_message = ""
    finalization_status = "failed"

    try:
        # 最終同期
        if os.path.exists(generated_assets_path):
            os.makedirs(output_directory, exist_ok=True)

            if os.path.isdir(generated_assets_path):
                # generated_assets_path の中身を output_directory にコピー（マージ）
                # dirs_exist_ok=True で output_directory が存在してもエラーにならない
                shutil.copytree(generated_assets_path, output_directory, dirs_exist_ok=True)
                sync_message = f"Assets from directory '{generated_assets_path}' successfully synced to '{output_directory}'."
            elif os.path.isfile(generated_assets_path):
                # ファイルを output_directory の中に、元のファイル名でコピー
                destination_file_path = os.path.join(output_directory, os.path.basename(generated_assets_path))
                shutil.copy2(generated_assets_path, destination_file_path)
                sync_message = f"Asset file '{generated_assets_path}' successfully synced to '{destination_file_path}'."
            else:
                tool_context.state["finalization_status"] = "failed"
                return f"Error: '{generated_assets_path}' is neither a file nor a directory. Cannot finalize assets."

            tool_context.state["final_assets_synced"] = True
            tool_context.state["final_output_path"] = output_directory
            finalization_status = "synced"

        else:
            tool_context.state["finalization_status"] = "failed"
            return f"Error: Generated assets path '{generated_assets_path}' does not exist. Cannot finalize assets."

        # クリーンアップ
        if os.path.exists(generated_assets_path):
            shutil.rmtree(generated_assets_path)
            cleanup_message = f"Generated assets path '{generated_assets_path}' cleaned up."
            tool_context.state["generated_assets_cleaned_up"] = True
            finalization_status = "completed"
        else:
            cleanup_message = f"Generated assets path '{generated_assets_path}' already removed or never existed. No cleanup needed."
            tool_context.state["generated_assets_cleaned_up"] = False
            if finalization_status == "synced":
                finalization_status = "completed_with_no_cleanup"

        tool_context.state["finalization_status"] = finalization_status
        return f"Finalization complete. {sync_message} {cleanup_message}"

    except Exception as e:
        tool_context.state["finalization_status"] = "failed"
        tool_context.state["finalization_error"] = str(e)
        return f"Error during asset finalization: {e}"