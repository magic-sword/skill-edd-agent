from pydantic import BaseModel, Field

class Input(BaseModel):
    """単体テスト生成スキルの入力パラメータを表すスキーマモデル。"""
    skill: str = Field(..., description='単体テストを生成する対象のスキル名。')

class Output(BaseModel):
    """単体テスト生成スキルの出力結果を表すスキーマモデル。"""
    value: str = Field(..., description='スキル実行結果の出力メッセージ')
