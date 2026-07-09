import os
import subprocess
import shutil
import tempfile
from typing import Any
from google.genai import types
from .base import BaseGeminiClient

class AgyGeminiClient(BaseGeminiClient):
    """Antigravity CLI (agy) を使用してプロンプトを実行するクライアント。"""
    def __init__(self):
        pass

    def generate_content(
        self,
        contents: Any,
        config: types.GenerateContentConfig | None = None,
        model: str | None = None,
        **kwargs: Any
    ) -> types.GenerateContentResponse:
        """Antigravity CLI (agy) を使用してプロンプトを実行し、一時ディレクトリ経由でファイルを渡します。"""
        from .request import GeminiRequest
        if isinstance(contents, GeminiRequest):
            actual_contents = contents.build()
            attached_files = contents.attached_files
        else:
            actual_contents = contents
            attached_files = []

        scratch_dir = "/workspace/scratch"
        if not os.path.exists(scratch_dir):
            os.makedirs(scratch_dir)
        temp_dir = tempfile.mkdtemp(dir=scratch_dir, prefix="agy_temp_")
        
        try:
            # 添付ファイルを一時ディレクトリへコピー
            copied_files_info = []
            for file_path, ref_root in attached_files:
                if not os.path.exists(file_path):
                    continue
                rel_path = os.path.relpath(file_path, ref_root)
                dest_path = os.path.join(temp_dir, rel_path)
                dest_dir = os.path.dirname(dest_path)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                shutil.copy2(file_path, dest_path)
                copied_files_info.append(rel_path)

            # プロンプト本文の組み立て
            prompt_parts = []
            if isinstance(actual_contents, list):
                for part in actual_contents:
                    if isinstance(part, str):
                        # 重複する巨大な添付ファイルやシステムルールのテキストはプロンプト本文から除外する
                        if part.startswith("# --- File:") or part.startswith("# --- System Rule:"):
                            continue
                        prompt_parts.append(part)
            elif isinstance(actual_contents, str):
                prompt_parts.append(actual_contents)

            main_prompt = "\n".join(prompt_parts)

            # agy用プロンプトに一時ディレクトリのファイル情報を追記
            instruction_lines = [
                main_prompt,
                "\n[System Information]",
                "以下のディレクトリに必要な参考ファイルやコードが配置されています。",
                "これらのファイルを参考に、指示に従ってください。",
                f"- 参考ディレクトリ: {temp_dir}"
            ]
            if copied_files_info:
                instruction_lines.append("配置されたファイル一覧:")
                for f_rel in copied_files_info:
                    instruction_lines.append(f"  * {f_rel}")

            agy_prompt = "\n".join(instruction_lines)

            # agy コマンドのパス解決
            agy_path = os.path.expanduser("~/.local/bin/agy")
            if not os.path.exists(agy_path):
                agy_path = "agy"

            cmd = [
                agy_path,
                "--add-dir", temp_dir,
                "--dangerously-skip-permissions",
                "--print", agy_prompt
            ]

            env = os.environ.copy()
            env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"

            # agyを実行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"agy command failed with code {result.returncode}.\n"
                    f"stdout: {result.stdout}\n"
                    f"stderr: {result.stderr}"
                )

            response_text = result.stdout.strip()

            # types.GenerateContentResponse に見せかけたダミーのパースオブジェクトを構築
            dummy_part = types.Part(text=response_text)
            dummy_content = types.Content(parts=[dummy_part])
            dummy_candidate = types.Candidate(content=dummy_content)
            response_obj = types.GenerateContentResponse(candidates=[dummy_candidate])

            return response_obj

        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
