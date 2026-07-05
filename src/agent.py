"""
A2Aプロトコル互換のエージェント・エントリーポイント。
環境変数（ADK_EVAL_MODE）を識別し、適切なエージェント実体をエクスポートします。
"""
import sys
import pathlib

# agentsモジュールを確実にロードできるように、親ディレクトリを sys.path に追加します
current_dir = pathlib.Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from agents.common import is_eval_mode

if is_eval_mode:
    # 評価モード時：共通パッケージの SkillRegistry から評価対象のスキルだけを動的ロードしてエージェントを構築
    from google.adk import Agent
    from edd_agent_tools.registry import SkillRegistry

    import os
    # 評価対象スキルの特定 (CLI引数 --skill と対称な環境変数 SKILL を使用)
    target_eval_skill = os.environ.get("SKILL")

    registry = SkillRegistry()
    skills_to_load = [target_eval_skill] if target_eval_skill else []
    agent_tools = [registry.get_skill(name).get_tool() for name in skills_to_load]

    print(f"DEBUG: loaded_skills = {skills_to_load}", file=sys.stderr)

    root_agent = Agent(
        model='gemini-2.5-flash',
        name='evaluation_driven_development_agent',
        instruction=(
            "あなたは自立的評価駆動開発エージェントです。\n"
            "ロードされたスキル（ツール）を用いて、ユーザーからの指示やタスクを正常に遂行してください。"
        ),
        tools=agent_tools
    )
else:
    # 通常起動時は、システム開発支援用のワークフロー指示を持ったエージェントをロード
    from agents.system_agent import system_agent as root_agent
