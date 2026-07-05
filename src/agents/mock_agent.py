from typing import Any
from google.adk.tools import ToolContext

# モック用の before_tool_callback (Environment Simulation)
async def before_tool_callback(tool: Any, args: dict[str, Any], tool_context: ToolContext) -> Any:
    if tool.name == "load_skill":
        skill_name = args.get("skill") or args.get("skill_name")
        agent_name = tool_context.agent_name
        state_key = f"_adk_activated_skill_{agent_name}"
        activated_skills = list(tool_context.state.get(state_key) or [])
        if skill_name not in activated_skills:
            activated_skills.append(skill_name)
            tool_context.state[state_key] = activated_skills
            
        # 辞書を返すことで、実ツールの実行をスキップし、この返り値をツールコールの結果にする (モック実行)
        return {
            "skill": skill_name,
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
    return None
