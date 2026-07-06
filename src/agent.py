"""A2Aプロトコル互換のエージェント・エントリーポイント。"""
import sys
from google.adk import Agent
from google.adk.tools import skill_toolset
from google.adk.tools.environment import EnvironmentToolset
from google.adk.environment import LocalEnvironment
from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor
from google.adk.skills import load_skill_from_dir
from edd_agent_tools.skills import SkillsState, SkillTier

# state を用いて全登録スキルを解決
state = SkillsState()
skills = state.list_skills()

# システムスキル定義
system_skills = {"skill-generator", "skill-manager", "trigger-evaluator", "eval-unit-tester", "test-executor"}

# ADKのSkillオブジェクトリストへマップ (Tier 0のものは除外、システムスキルは常に含める)
loaded_skills = []
for skill in skills:
    # Tier 0 (SANDBOX) のスキルは排除
    if skill._tier == SkillTier.SANDBOX and skill.name not in system_skills:
        continue
    try:
        adk_skill = load_skill_from_dir(skill.root_dir)
        loaded_skills.append(adk_skill)
    except Exception as e:
        print(f"Warning: Failed to load skill from {skill.root_dir}: {e}", file=sys.stderr)

agent_tools = [
    # 登録スキルをロードするためのツールセット
    skill_toolset.SkillToolset(
        skills=loaded_skills,
        code_executor=UnsafeLocalCodeExecutor()
    ),
    # 開発スクリプトをシェル経由で実行するためのツールセット
    EnvironmentToolset(environment=LocalEnvironment())
]

root_agent = Agent(
    model='gemini-2.5-flash',
    name='system_development_agent',
    instruction=(
        "あなたは評価駆動開発プロジェクトの開発・管理を支援するシステムエージェントです。\n"
        "提供されたシステムスキルや各種ツールを用いて、指示された開発タスクやスキルの生成・管理処理を正確に実行してください。"
    ),
    tools=agent_tools
)
