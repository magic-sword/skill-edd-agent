import json
from abc import ABC, abstractmethod
from typing import Any
from .schemas import (
    EvalConfig,
    Criteria,
    ConversationTurn,
    IntermediateData,
    ToolUse,
    ToolResponse
)

class OutputModeStrategy(ABC):
    """出力モードごとのプロンプト生成および評価基準戦略を定義する抽象基底クラス。

    このクラスを継承する具象クラスは、それぞれの出力モードに応じた
    プロンプト指示のオーバーライドロジック、および最適な評価基準設定を提供します。
    """

    @abstractmethod
    def get_instruction_override(self) -> str:
        """プロンプトに含める指示のオーバーライド文字列を返します。

        Returns:
            str: プロンプトに含める具体的な指示文字列。
        """
        pass

    def build_prompt(self, template: str, skill_content: str, schema_str: str) -> str:
        """指定されたテンプレートにスキルの仕様書およびPydanticスキーマを埋め込み、最終プロンプトを構築します。

        Args:
            template: ロードされたプロンプトテンプレート文字列。
            skill_content: 対象スキルの仕様書内容。
            schema_str: ターゲットの入力スキーマ定義。

        Returns:
            str: 最終置換済みのプロンプトテキスト。
        """
        return template.replace(
            "{skill_content}", skill_content
        ).replace(
            "{pydantic_schema}", schema_str
        ).replace(
            "{instruction_override}", self.get_instruction_override()
        )

    def get_eval_config(self, eval_set_path: str) -> EvalConfig:
        """この出力モードに最適な評価構成設定（EvalConfig）オブジェクトを返します。

        Args:
            eval_set_path: 評価セットファイルの絶対パス。

        Returns:
            EvalConfig: 各出力モード特性に最適化された評価設定モデル。
        """
        # デフォルト戦略（ValueOnlyおよびConversational）では一致スコア0.8を設定
        return EvalConfig(
            eval_set_path=eval_set_path,
            threshold_accuracy=1.0,
            criteria=Criteria(response_match_score=0.8)
        )

    def build_conversation_turn(
        self,
        tool_name: str,
        index: int,
        user_instruction: str,
        expected_output: str,
        input_args: dict | Any
    ) -> ConversationTurn:
        """この出力モードに最適な会話ターン（ConversationTurn）オブジェクトを組み立てて返します。

        Args:
            tool_name: 対象スキルのツール名。
            index: テストケースのインデックス（0開始）。
            user_instruction: ユーザーの指示。
            expected_output: 期待される最終応答テキスト。
            input_args: ツール実行に渡される型安全な引数。

        Returns:
            ConversationTurn: 各モードに適合するように組み立てられた会話ターンモデルオブジェクト。
        """
        # デフォルトは単純な文字列結果として格納
        return ConversationTurn(
            invocation_id=f"inv_{index+1:03d}",
            user_content={
                "role": "user",
                "parts": [{"text": user_instruction}]
            },
            final_response={
                "role": "model",
                "parts": [{"text": expected_output}]
            },
            intermediate_data=IntermediateData(
                tool_uses=[ToolUse(name=tool_name, args=input_args)],
                tool_responses=[ToolResponse(name=tool_name, response={"result": expected_output})]
            )
        )


class ValueOnlyStrategy(OutputModeStrategy):
    """'VALUE_ONLY' 出力モードに対応するプロンプト戦略クラス。

    この戦略では、生成されるテストケースの期待応答が、
    余計な解説を一切含まない純粋な結果となるよう指示します。
    """

    def get_instruction_override(self) -> str:
        """'VALUE_ONLY' モード用のプロンプト指示オーバーライド文字列を返します。

        Returns:
            str: プロンプトに含める具体的な指示文字列。
        """
        return (
            "会話内のユーザー入力には必ず「〜〜の結果のみを出力してください」という制約を含め、"
            "期待応答（expected_output）は余計な解説を一切排した結果そのもの（例: 大文字化されたテキストのみ）としてください。"
        )


class ConversationalStrategy(OutputModeStrategy):
    """'CONVERSATIONAL' 出力モードに対応するプロンプト戦略クラス。

    この戦略では、生成されるテストケースの期待応答が、
    ユーザーとの自然な対話形式となるよう指示します。
    """

    def get_instruction_override(self) -> str:
        """'CONVERSATIONAL' モード用のプロンプト指示オーバーライド文字列を返します。

        Returns:
            str: プロンプトに含める具体的な指示文字列。
        """
        return (
            "会話内のユーザー入力は自然なメッセージ（制約なし）とし、期待応答（expected_output）は"
            "ユーザーに対する自然な対話応答メッセージ（例: 「〜〜を処理しました。結果は〜〜です。」など）としてください。"
        )


class StructuredJsonStrategy(OutputModeStrategy):
    """'STRUCTURED_JSON' 出力モードに対応するプロンプト戦略クラス。

    この戦略では、生成されるテストケースの期待応答が、
    純粋な JSON 文字列となるよう指示します。
    """

    def get_instruction_override(self) -> str:
        """'STRUCTURED_JSON' モード用のプロンプト指示オーバーライド文字列を返します。

        Returns:
            str: プロンプトに含める具体的な指示文字列。
        """
        return (
            "期待応答（expected_output）は余計な解説を一切排した生の JSON 文字列（例: {\"result_message\": \"〜〜\"}）"
            "のみとし、自然言語テキストは絶対に含めないでください。"
        )

    def get_eval_config(self, eval_set_path: str) -> EvalConfig:
        """'STRUCTURED_JSON' モード用に最適化された、厳格な完全一致判定(1.0)基準を持つ評価構成設定を返します。

        Args:
            eval_set_path: 評価セットファイルの絶対パス。

        Returns:
            EvalConfig: response_match_score が 1.0 に厳格化された評価設定モデル。
        """
        return EvalConfig(
            eval_set_path=eval_set_path,
            threshold_accuracy=1.0,
            criteria=Criteria(response_match_score=1.0)
        )

    def build_conversation_turn(
        self,
        tool_name: str,
        index: int,
        user_instruction: str,
        expected_output: str,
        input_args: dict | Any
    ) -> ConversationTurn:
        """STRUCTURED_JSON モードでは、期待応答を JSON 辞書としてパースしてツールレスポンスに直接設定します。

        Args:
            tool_name: 対象スキルのツール名。
            index: テストケースのインデックス（0開始）。
            user_instruction: ユーザーの指示。
            expected_output: 期待される最終応答JSONテキスト。
            input_args: ツール実行に渡される型安全な引数。

        Returns:
            ConversationTurn: json.loads にてパースされた結果が response に設定された会話ターンモデルオブジェクト。
        """
        try:
            parsed_response = json.loads(expected_output)
            if not isinstance(parsed_response, dict):
                parsed_response = {"result": parsed_response}
        except Exception:
            parsed_response = {"result": expected_output}

        return ConversationTurn(
            invocation_id=f"inv_{index+1:03d}",
            user_content={
                "role": "user",
                "parts": [{"text": user_instruction}]
            },
            final_response={
                "role": "model",
                "parts": [{"text": expected_output}]
            },
            intermediate_data=IntermediateData(
                tool_uses=[ToolUse(name=tool_name, args=input_args)],
                tool_responses=[ToolResponse(name=tool_name, response=parsed_response)]
            )
        )


def get_output_mode_strategy(skill_content: str) -> OutputModeStrategy:
    """スキルの仕様書の内容に基づき、適切な OutputModeStrategy 具象クラスのインスタンスを返します。

    Args:
        skill_content: スキルの仕様書（SKILL.md）の内容文字列。

    Returns:
        OutputModeStrategy: 検出された出力モードに対応する戦略オブジェクト。
    """
    if "Output Mode: CONVERSATIONAL" in skill_content:
        return ConversationalStrategy()
    elif "Output Mode: STRUCTURED_JSON" in skill_content:
        return StructuredJsonStrategy()
    else:
        return ValueOnlyStrategy()
