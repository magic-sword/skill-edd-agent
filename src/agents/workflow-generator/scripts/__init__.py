from google.adk import Agent
from .handler import process_message, SKILL_METADATA
from .models import Input

# workflow-generator 自身を表すエージェントオブジェクトの定義と公開
workflow_agent = Agent(
    model='gemini-2.5-flash',
    name='workflow_generator_agent',
    instruction=(
        "あなたは Google ADK 互換の新しいワークフローエージェントを自律生成・構成するエージェントです。\n"
        "ロードされた workflow-generator ツールを呼び出して、指示されたワークフローの生成処理を正確に実行してください。"
    ),
    tools=[process_message]
)
