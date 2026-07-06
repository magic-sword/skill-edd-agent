from typing import Any
from pydantic import BaseModel, Field

class ToolUse(BaseModel):
    """評価実行時に実行される単一のツール呼び出し定義。"""
    name: str = Field(..., description="呼び出すツール関数名")
    args: dict[str, Any] = Field(..., description="ツール関数に引き渡す引数")

class ToolResponse(BaseModel):
    """呼び出されたツール関数から返される期待結果定義。"""
    name: str = Field(..., description="ツール関数名")
    response: dict[str, Any] = Field(..., description="ツール関数から返される期待結果の辞書")

class IntermediateData(BaseModel):
    """シミュレーション中に発生する中間推論およびツール呼び出しのリスト。"""
    tool_uses: list[ToolUse] = Field(..., description="中間ツール呼び出しのリスト")
    tool_responses: list[ToolResponse] = Field(..., description="中間ツールレスポンスのリスト")

class ConversationTurn(BaseModel):
    """会話の1ターン（ユーザー入力、ツール実行、モデルの期待返答）をカプセル化するモデル。"""
    invocation_id: str = Field(..., description="ターンの識別子 (例: inv_001)")
    user_content: dict[str, Any] = Field(..., description="ユーザーからの入力コンテンツ構造")
    final_response: dict[str, Any] = Field(..., description="モデルからの期待される最終返答コンテンツ構造")
    intermediate_data: IntermediateData = Field(..., description="中間ツール呼び出し情報")

class SessionInput(BaseModel):
    """シミュレーションセッションの初期入力状態。"""
    state: dict[str, Any] = Field(..., description="初期セッションのステート引数")
    app_name: str = Field("evaluation_driven_development_agent", description="評価を実行するアプリケーション名")
    user_id: str = Field("user", description="ユーザーID")

class EvalCase(BaseModel):
    """単一の評価テストケース全体の構造モデル。"""
    eval_id: str = Field(..., description="評価ケースのユニーク識別子")
    conversation: list[ConversationTurn] = Field(..., description="会話のターンのリスト")
    session_input: SessionInput = Field(..., description="セッション初期ステート")

class Criteria(BaseModel):
    """詳細な評価基準パラメータ。"""
    response_match_score: float = Field(0.8, description="応答の一致スコア閾値 (0.0〜1.0)")

class EvalConfig(BaseModel):
    """単体テスト評価スイートの実行しきい値や構成を設定するモデル。"""
    eval_set_path: str = Field(..., description="評価用データセットファイル（*.evalset.json）への相対/絶対パス")
    threshold_accuracy: float = Field(1.0, description="合格となる最小精度閾値 (0.0〜1.0)")
    criteria: Criteria = Field(default_factory=Criteria, description="詳細な評価基準パラメータ")

class TestParameterCase(BaseModel):
    """単一のテストパラメータケースを定義するPydanticモデル。

    ユーザーの指示、ツールへの入力パラメータ、および期待される出力を含みます。
    """
    user_instruction: str = Field(
        ...,
        description="ユーザーからの自然言語での指示（例: 『hello worldを大文字にしてください』など）"
    )
    input_parameters: dict = Field(
        ...,
        description="ツールに渡す引数（args）の辞書。キー名は仕様書（SKILL.md）の引数に従ってください。"
    )
    expected_output: str = Field(
        ...,
        description="ツールまたはエージェントからの期待される最終的なテキスト応答（例: 'HELLO WORLD'）"
    )

    def to_eval_case(self, tool_name: str, index: int, strategy: Any) -> EvalCase:
        """テストパラメータケースを、型安全な EvalCase モデルオブジェクトに自律マッピング・変換します。

        Args:
            tool_name: 評価対象のスキル・ツール名。
            index: テストケースのインデックス番号。
            strategy: 出力モードに対応する戦略オブジェクト。

        Returns:
            EvalCase: 型安全に構築された EvalCase のインスタンス。
        """
        input_args = self.input_parameters
        if hasattr(input_args, "model_dump"):
            input_args = input_args.model_dump()
        elif not isinstance(input_args, dict):
            input_args = {"text": str(input_args)}

        eval_id = f"{tool_name}_happy_path_{index+1:03d}"

        # 戦略オブジェクトに会話ターンの構築をポリモーフィズムで委譲
        turn = strategy.build_conversation_turn(
            tool_name=tool_name,
            index=index,
            user_instruction=self.user_instruction,
            expected_output=self.expected_output,
            input_args=input_args
        )

        return EvalCase(
            eval_id=eval_id,
            conversation=[turn],
            session_input=SessionInput(
                state=input_args,
                app_name="evaluation_driven_development_agent",
                user_id="user"
            )
        )

class TestParameterSet(BaseModel):
    """複数のテストケースをまとめたセットを定義するPydanticモデル。"""
    cases: list[TestParameterCase] = Field(..., description="生成されたテストパラメータケースのリスト")

class EvalSet(BaseModel):
    """アセット保存用に、評価ケース一式を格納するテストスイート全体を表すモデル。"""
    eval_set_id: str = Field(..., description="評価セットID")
    name: str = Field(..., description="評価セットの名称")
    description: str = Field(..., description="評価セットの詳細説明")
    eval_cases: list[EvalCase] = Field(..., description="全評価テストケースのリスト")
