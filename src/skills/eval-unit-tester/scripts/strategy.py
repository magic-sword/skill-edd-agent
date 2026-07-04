from abc import ABC, abstractmethod

class OutputModeStrategy(ABC):
    """Output Modeごとのプロンプト制御を行うストラテジー抽象クラス"""
    @abstractmethod
    def get_instruction_override(self) -> str:
        pass

class ValueOnlyStrategy(OutputModeStrategy):
    """VALUE_ONLY用のプロンプトストラテジー"""
    def get_instruction_override(self) -> str:
        return (
            "会話内のユーザー入力には必ず「〜〜の結果のみを出力してください」という制約を含め、"
            "期待応答（expected_output）は余計な解説を一切排した結果そのもの（例: 大文字化されたテキストのみ）としてください。"
        )

class ConversationalStrategy(OutputModeStrategy):
    """CONVERSATIONAL用のプロンプトストラテジー"""
    def get_instruction_override(self) -> str:
        return (
            "会話内のユーザー入力は自然なメッセージ（制約なし）とし、期待応答（expected_output）は"
            "ユーザーに対する自然な対話応答メッセージ（例: 「〜〜を処理しました。結果は〜〜です。」など）としてください。"
        )

class StructuredJsonStrategy(OutputModeStrategy):
    """STRUCTURED_JSON用のプロンプトストラテジー"""
    def get_instruction_override(self) -> str:
        return (
            "期待応答（expected_output）は余計な解説を一切排した生の JSON 文字列（例: {\"result_message\": \"〜〜\"}）"
            "のみとし、自然言語テキストは絶対に含めないでください。"
        )

def get_output_mode_strategy(skill_content: str) -> OutputModeStrategy:
    """仕様書の内容に基づいて、対応する OutputModeStrategy 具象クラスのインスタンスを返します"""
    if "Output Mode: CONVERSATIONAL" in skill_content:
        return ConversationalStrategy()
    elif "Output Mode: STRUCTURED_JSON" in skill_content:
        return StructuredJsonStrategy()
    else:
        return ValueOnlyStrategy()
