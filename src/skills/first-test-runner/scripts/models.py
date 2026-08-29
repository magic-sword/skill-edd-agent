from pydantic import BaseModel, Field


class Tier1SkillOnboardingOutput(BaseModel):
    onboarding_status: str = Field(..., description="スキルオンボーディングの全体的なステータス ('success' または 'failed')。")
    message: str = Field(..., description='オンボーディングプロセスに関する詳細メッセージ。')
