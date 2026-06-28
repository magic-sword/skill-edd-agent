"""
A2Aプロトコル互換の自立的評価駆動開発エージェントのコア定義。
"""
from google.adk import Agent

# Google ADK 2.0 に準拠したエージェントを定義します。
# 将来的にこのエージェントにスキルやツールを追加して自立的開発を行えるようにします。
root_agent = Agent(
    model='gemini-2.0-flash',
    name='evaluation_driven_development_agent',
    instruction=(
        "あなたは自立的評価駆動開発エージェントです。\n"
        "ユーザーの指示に従い、評価駆動でスキルを開発・統合する能力を持ちます。"
    )
)
