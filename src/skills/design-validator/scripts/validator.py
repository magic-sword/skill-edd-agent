import json
import os
from typing import Dict, Any
from edd_agent_tools.skills import SkillsState
from .models import ValidateDesignOutput
from .client import GeminiClient
from .prompter import PromptBuilder

class DesignValidator:
    """スキル設計と実装の整合性を検証するクラス。"""

    def __init__(self):
        self._gemini_client = GeminiClient()
        self._prompt_builder = PromptBuilder()

    def _read_skill_file(self, skill_obj: Any, file_name: str) -> str:
        """指定されたスキルのファイルを読み込みます。"""
        if file_name == "design.json":
            file_path = os.path.join(skill_obj.root_dir, "assets", "design.json")
        else:
            file_path = os.path.join(skill_obj.root_dir, file_name)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"ファイルが存在しません: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"ファイル '{file_path}' の読み込み中にエラーが発生しました: {e}")

    def validate_skill(self, skill: str) -> ValidateDesignOutput:
        """
        指定されたスキルの設計と実装の整合性を検証します。

        Args:
            skill: 検証対象のスキル名。

        Returns:
            ValidateDesignOutput: 検証結果。
        """
        try:
            state = SkillsState()
            skill_obj = state.get_skill(skill)

            design_json_content = self._read_skill_file(skill_obj, "design.json")
            models_py_content = self._read_skill_file(skill_obj, "scripts/models.py")
            handler_py_content = self._read_skill_file(skill_obj, "scripts/handler.py")
            
            executor_py_content = self._read_skill_file(skill_obj, "scripts/executor.py")

            prompt = self._prompt_builder.build_validation_prompt(
                design_json=design_json_content,
                models_py=models_py_content,
                handler_py=handler_py_content,
                executor_py=executor_py_content
            )

            gemini_response = self._gemini_client.call_gemini_api(prompt, response_schema=ValidateDesignOutput)
            gemini_output_text = gemini_response.text

            try:
                validation_result: Dict = json.loads(gemini_output_text)
                return ValidateDesignOutput(
                    status=validation_result.get("status", "failed"),
                    details=validation_result.get("details", ""),
                    score=float(validation_result.get("score", 0.0))
                )
            except json.JSONDecodeError as e:
                return ValidateDesignOutput(
                    status="failed",
                    details=f"Gemini APIからの応答が不正なJSON形式です: {e}\n応答内容: {gemini_output_text}",
                    score=0.0
                )

        except RuntimeError as e:
            return ValidateDesignOutput(
                status="failed",
                details=f"検証中にエラーが発生しました: {e}",
                score=0.0
            )
        except Exception as e:
            return ValidateDesignOutput(
                status="failed",
                details=f"予期せぬエラーが発生しました: {type(e).__name__}: {e}",
                score=0.0
            )
