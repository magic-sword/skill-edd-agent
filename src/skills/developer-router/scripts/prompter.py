import os
from google.genai import types


class PromptBuilder:
    """Gemini API に送信するルーティング判定プロンプトを構築する責務を持つクラス。"""

    def __init__(self):
        self._prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """プロンプトテンプレートファイルを読み込みます。"""
        current_dir = os.path.dirname(__file__)
        template_path = os.path.join(current_dir, "../assets/prompts/routing_prompt.txt")
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise RuntimeError(f"プロンプトテンプレートファイルが見つかりません: {template_path}")

    def build_routing_prompt(self, prompt: str, existing_skills: list[dict]) -> list[types.ContentType]:
        """
        既存スキル一覧と機能要件から、ルーティング判定用の Gemini プロンプトを構築します。

        Args:
            prompt: 開発したい機能の要件プロンプト。
            existing_skills: 既存スキルの情報のリスト。

        Returns:
            list[types.ContentType]: Gemini API に渡す Content オブジェクトのリスト。
        """
        # 既存スキル一覧のテキスト整形
        skills_text_list = []
        for s in existing_skills:
            skills_text_list.append(f"- スキル名: {s['name']}\n  説明: {s['description']}")
        skills_inventory_str = "\n".join(skills_text_list) if skills_text_list else "なし（既存スキルがまだ登録されていません）"

        full_prompt_text = self._prompt_template.format(
            skills_inventory=skills_inventory_str,
            requirement_prompt=prompt
        )

        # ContentType 構造に準拠した形式で返却
        return [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=full_prompt_text)
                ]
            )
        ]


def build_routing_prompt(prompt: str, existing_skills: list[dict]) -> list[types.ContentType]:
    """
    既存スキル一覧と機能要件から、ルーティング判定用の Gemini プロンプトを構築します。

    Args:
        prompt: 開発したい機能の要件プロンプト。
        existing_skills: 既存スキルの情報のリスト。

    Returns:
        list[types.ContentType]: Gemini API に渡す Content オブジェクトのリスト。
    """
    builder = PromptBuilder()
    return builder.build_routing_prompt(prompt, existing_skills)

