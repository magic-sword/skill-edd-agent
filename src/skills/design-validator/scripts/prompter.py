import os

class PromptBuilder:
    """Gemini API に送信するプロンプトを構築する責務を持つクラス。"""

    def __init__(self):
        self._prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """プロンプトテンプレートファイルを読み込みます。"""
        current_dir = os.path.dirname(__file__)
        template_path = os.path.join(current_dir, "../assets/prompts/validation_prompt.txt")
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise RuntimeError(f"プロンプトテンプレートファイルが見つかりません: {template_path}")

    def build_validation_prompt(self, design_json: str, models_py: str, handler_py: str, executor_py: str) -> str:
        """
        スキル設計と実装の整合性検証のためのプロンプトを構築します。

        Args:
            design_json: design.json の内容。
            models_py: models.py の内容。
            handler_py: handler.py の内容。
            executor_py: executor.py の内容。

        Returns:
            str: 構築されたプロンプト文字列。
        """
        return self._prompt_template.format(
            design_json=design_json,
            models_py=models_py,
            handler_py=handler_py,
            executor_py=executor_py
        )
