from google.adk import Agent
from .handler import process_message, SKILL_METADATA
from .models import Input, Output

# 構築されたエージェントオブジェクトを公開 (テストハーネスや親エージェントから参照可能)
workflow_agent = Agent(
    model='gemini-2.5-flash',
    name='skill_developer_agent',
    instruction=(
        "あなたは Google ADK 互換のワークフローエージェントです。\n"
        "ロードされた skill-developer ツールを呼び出して、処理を正確に実行してください。"
    ),
    tools=[process_message]
)
