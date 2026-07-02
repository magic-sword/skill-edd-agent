import sys
from google.adk import Agent
from google.adk.tools import skill_toolset
from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor
from agents.common import is_eval_mode, load_all_skills

# 評価対象スキルの特定
target_eval_skill = None
if is_eval_mode:
    for arg in sys.argv:
        if "skills/" in arg:
            parts = arg.split("skills/")
            if len(parts) > 1:
                skill_name = parts[1].split("/")[0]
                target_eval_skill = skill_name
                break

# 評価用エージェントではシステムスキルを完全に除外してロード
loaded_skills = load_all_skills(exclude_system=True, target_eval_skill=target_eval_skill)

agent_tools = [
    skill_toolset.SkillToolset(
        skills=loaded_skills,
        code_executor=UnsafeLocalCodeExecutor()
    )
]

user_agent = Agent(
    model='gemini-2.5-flash',
    name='evaluation_driven_development_agent',
    instruction=(
        "あなたは自立的評価駆動開発エージェントです。\n"
        "ロードされたスキル（ツール）を用いて、ユーザーからの指示やタスクを正常に遂行してください。"
    ),
    tools=agent_tools
)
