from google.adk import Agent
from google.adk.tools import skill_toolset
from google.adk.tools.environment import EnvironmentToolset
from google.adk.environment import LocalEnvironment
from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor
from agents.common import load_all_skills

# システム開発支援用エージェントでは、システムスキルも含めてロード
loaded_skills = load_all_skills(exclude_system=False)

agent_tools = [
    # 登録スキルをロードするためのツールセット
    skill_toolset.SkillToolset(
        skills=loaded_skills,
        code_executor=UnsafeLocalCodeExecutor()
    ),
    # 開発スクリプトをシェル経由で実行するためのツールセット
    EnvironmentToolset(environment=LocalEnvironment())
]

system_agent = Agent(
    model='gemini-2.5-flash',
    name='system_development_agent',
    instruction=(
        "あなたは評価駆動開発プロジェクトの開発・管理を支援するシステムエージェントです。\n"
        "提供されたシステムスキルや各種ツールを用いて、指示された開発タスクやスキルの生成・管理処理を正確に実行してください。"
    ),
    tools=agent_tools
)
