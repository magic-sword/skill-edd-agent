import sys
import os
from typing import Any
from google.adk.tools import ToolContext

# 実行中のデータセットからトリガー評価モード (モック有効) であるかを自律判定
is_trigger_eval_mode = False
for arg in sys.argv:
    if "_trigger.evalset" in arg:
        is_trigger_eval_mode = True
        break

# ADK公式の before_tool_callback を使ってモック・シミュレーションを実行する
async def before_tool_callback(tool: Any, args: dict[str, Any], tool_context: ToolContext) -> Any:
    # トリガー評価モードかつ load_skill ツール呼び出しの場合
    if is_trigger_eval_mode and tool.name == "load_skill":
        skill_name = args.get("skill_name")
        agent_name = tool_context.agent_name
        state_key = f"_adk_activated_skill_{agent_name}"
        activated_skills = list(tool_context.state.get(state_key) or [])
        if skill_name not in activated_skills:
            activated_skills.append(skill_name)
            tool_context.state[state_key] = activated_skills
            
        # 辞書を返すことで、実ツールの実行をスキップし、この返り値をツールコールの結果にする (モック実行)
        return {
            "skill_name": skill_name,
            "instructions": (
                f"スキルの指示のロードに成功しました。このスキル '{skill_name}' は正常にトリガーされました。\n"
                "タスクは完了しています。これ以上のツール実行（run_skill_script等）は一切行わず、"
                "『ロードが正常に完了しました』という旨の簡潔なメッセージを返して、処理を終了してください。"
            ),
            "frontmatter": {
                "name": skill_name,
                "description": f"Mock description for {skill_name}"
            }
        }
    return None # その他の場合はそのまま実ツールを実行

from google.adk import Agent
from google.adk.tools import skill_toolset
from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor
from agents.common import is_eval_mode, load_all_skills

# 評価対象スキルの特定
target_eval_skill = os.environ.get("TARGET_EVAL_SKILL")
if not target_eval_skill and is_eval_mode:
    for arg in sys.argv:
        if "skills/" in arg:
            parts = arg.split("skills/")
            if len(parts) > 1:
                skill_name = parts[1].split("/")[0]
                target_eval_skill = skill_name
                break

# 評価用エージェントではシステムスキルを完全に除外してロード
loaded_skills = load_all_skills(exclude_system=True, target_eval_skill=target_eval_skill)
print(f"DEBUG: loaded_skills = {[s.name for s in loaded_skills]}", file=sys.stderr)

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
    tools=agent_tools,
    before_tool_callback=before_tool_callback
)
