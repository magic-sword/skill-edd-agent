"""
A2Aプロトコル互換のエージェント・エントリーポイント。
"""
import sys
from google.adk import Agent
from google.adk.tools.environment import EnvironmentToolset
from google.adk.environment import LocalEnvironment
from edd_agent_tools.skills import SkillsState, SkillTier

# 全ての登録スキルおよびワークフローエージェントを解決
state = SkillsState()
skills = state.list_skills()

# システムスキル定義
system_skills = {
    "skill-creator", "skill-optimizer", "skill-diagnoser", 
    "skill-planner", "test-executor", "test-generator",
    "first-test-runner", "tier2-test-runner", "tier3-test-runner"
}

# 登録スキルおよびワークフローエージェントをツールとしてロードする
# Tier 0 (SANDBOX) のものは除外し、システムスキルは常に含める
agent_tools = []
for skill in skills:
    # Tier 0 (SANDBOX) のスキルは排除
    if skill.tier == SkillTier.SANDBOX and skill.name not in system_skills:
        continue
    try:
        # edd_agent_tools の Skill.get_tools() を使用して ADK 互換の FunctionTool リストを取得
        tools = skill.get_tools()
        agent_tools.extend(tools)
    except Exception as e:
        print(f"Warning: {skill.name} のツールロードに失敗しました: {e}", file=sys.stderr)

# 開発スクリプトをシェル経由で実行するためのツールセットも追加
agent_tools.append(EnvironmentToolset(environment=LocalEnvironment()))

root_agent = Agent(
    model='gemini-2.5-flash',
    name='evaluation_driven_development_agent',
    description='Google ADK を利用した、自立的にスキルを開発・統合するA2Aプロトコル互換のエージェントの土台',
    instruction=(
        "あなたは評価駆動開発（EDD）プロジェクトの管理および開発を実行する統合エージェントです。\n"
        "登録されたスキルやワークフローエージェントを適切に選択し、開発プロセスを自動的に実行してください。"
    ),
    tools=agent_tools
)
