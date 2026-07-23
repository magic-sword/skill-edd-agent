from pydantic import BaseModel, Field


class Tier2TestRunnerOutput(BaseModel):
    overall_status: str = Field(..., description="ワークフロー全体の最終ステータス（'success'または'failed'）。")
    contract_test_status: str = Field(..., description='契約テストの実行ステータス。')
    golden_test_status: str = Field(..., description='ゴールデンテストの実行ステータス。')
    judge_test_status: str = Field(..., description='ジャッジテストの実行ステータス。')
    tier2_registration_status: str = Field(..., description='Tier 2登録の最終ステータス。')
