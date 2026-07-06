from typing import Any, List, Dict
from pydantic import BaseModel, Field

class ToolUse(BaseModel):
    """評価実行時に実行される単一のツール呼び出し定義。"""
    name: str = Field(..., description="呼び出すツール関数名")
    args: Dict[str, Any] = Field(..., description="ツール関数に引き渡す引数")

class IntermediateData(BaseModel):
    """シミュレーション中に発生する中間推論およびツール呼び出しのリスト。"""
    tool_uses: List[ToolUse] = Field(..., description="中間ツール呼び出しのリスト")

class ConversationTurn(BaseModel):
    """会話の1ターン（ユーザー入力、ツール実行、モデルの期待返答）をカプセル化するモデル。"""
    invocation_id: str = Field(..., description="ターンの識別子 (例: inv_pos_001)")
    user_content: Dict[str, Any] = Field(..., description="ユーザーからの入力コンテンツ構造")
    final_response: Dict[str, Any] = Field(..., description="モデルからの期待される最終返答コンテンツ構造")
    intermediate_data: IntermediateData = Field(..., description="中間ツール呼び出し情報")

class SessionInput(BaseModel):
    """シミュレーションセッションの初期入力状態。"""
    app_name: str = Field(..., description="評価を実行するアプリケーション名")
    user_id: str = Field(..., description="ユーザーID")

class EvalCase(BaseModel):
    """単一の評価テストケース全体の構造モデル。"""
    eval_id: str = Field(..., description="評価ケースのユニーク識別子")
    conversation: List[ConversationTurn] = Field(..., description="会話のターンのリスト")
    session_input: SessionInput = Field(..., description="セッション初期ステート")

class EvalSet(BaseModel):
    """アセット保存用に、評価ケース一式を格納するテストスイート全体を表すモデル。"""
    eval_set_id: str = Field(..., description="評価セットID")
    name: str = Field(..., description="評価セットの名称")
    eval_cases: List[EvalCase] = Field(..., description="全評価テストケースのリスト")

class StaticEvalResult(BaseModel):
    """SKILL.mdの静的評価結果を表すスキーマ。"""
    specificity: int = Field(..., description="SKILL.mdの具体性の評価スコア (1-5)")
    clarity: int = Field(..., description="SKILL.mdの明確性の評価スコア (1-5)")
    feedback: str = Field(..., description="評価結果に基づくフィードバック")

class TriggerTestCase(BaseModel):
    """トリガー評価用テストケースの単一プロンプトを表すスキーマ。"""
    text: str = Field(..., description="生成されたプロンプトテキスト")

    def to_eval_case(self, skill_name: str, index: int, is_positive: bool = True) -> EvalCase:
        """このテストケースを、型安全な EvalCase モデルオブジェクトに自律マッピング・変換します。

        Args:
            skill_name: ターゲットのスキル名。
            index: テストケースのインデックス番号。
            is_positive: ポジティブテストケースであるか（Falseの場合はネガティブ）。

        Returns:
            EvalCase: 型安全に構築された EvalCase のインスタンス。
        """
        tool_uses = []
        if is_positive:
            tool_uses.append(ToolUse(name="load_skill", args={"skill_name": skill_name}))

        turn = ConversationTurn(
            invocation_id=f"inv_{'pos' if is_positive else 'neg'}_{index+1}",
            user_content={
                "role": "user",
                "parts": [{"text": self.text}]
            },
            final_response={
                "role": "model",
                "parts": [{"text": "Dummy"}]
            },
            intermediate_data=IntermediateData(
                tool_uses=tool_uses
            )
        )

        return EvalCase(
            eval_id=f"{'positive' if is_positive else 'negative'}_{index+1}",
            conversation=[turn],
            session_input=SessionInput(
                app_name="evaluation_driven_development_agent",
                user_id="user"
            )
        )

class TriggerTestCases(BaseModel):
    """トリガー評価用テストケースのリストを表すスキーマ。"""
    positive_prompts: List[TriggerTestCase] = Field(..., description="ポジティブなトリガープロンプトのリスト")
    negative_prompts: List[TriggerTestCase] = Field(..., description="ネガティブなトリガープロンプトのリスト")

class TriggerEvalReport(BaseModel):
    """トリガー静的評価結果および生成ファイルパスを記録する詳細レポートモデル。"""
    skill: str = Field(..., description="評価されたスキル名")
    static_evaluation: Dict[str, Any] = Field(..., description="静的評価詳細データ")
    generated_cases_file: str = Field(..., description="生成されたテストアセットファイルのパス")
    status: str = Field(..., description="総合結果ステータス ('PASSED' または 'FAILED')")
    evaluation_date: str = Field(..., description="評価が実施されたタイムスタンプ文字列")

class TrajectoryConfig(BaseModel):
    """軌跡スコアしきい値とマッチング形式の構成設定モデル。"""
    threshold: float = Field(1.0, description="軌跡合格判定しきい値スコア")
    match_type: str = Field("ANY_ORDER", description="軌跡マッチング形式")

class TriggerCriteria(BaseModel):
    """トリガー軌跡評価の基準パラメータモデル。"""
    tool_trajectory_avg_score: TrajectoryConfig = Field(default_factory=TrajectoryConfig, description="平均軌跡スコア基準")

class TriggerEvalConfig(BaseModel):
    """トリガー評価の全体的な構成設定モデル。"""
    criteria: TriggerCriteria = Field(default_factory=TriggerCriteria, description="トリガー軌跡評価基準定義")
