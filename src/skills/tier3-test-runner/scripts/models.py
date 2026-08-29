from pydantic import BaseModel, Field


class Tier3TestRunnerOutput(BaseModel):
    overall_status: str = Field(..., description="ワークフロー全体の最終ステータス（'success'または'failed'）。")
    contract_test_status: str = Field(..., description='契約テストの実行ステータス。')
    golden_test_status: str = Field(..., description='ゴールデンテストの実行ステータス。')
    judge_test_status: str = Field(..., description='ジャッジテストの実行ステータス。')
    adversarial_test_status: str = Field(..., description='敵対的・限界テストの実行ステータス。')
    tier3_registration_status: str = Field(..., description='Tier 3登録の最終ステータス。')
