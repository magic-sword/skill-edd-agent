"""
A2Aプロトコル互換の自立的評価駆動開発エージェントのコア定義。
"""
import pathlib
from google.adk import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset
from google.adk.tools.environment import EnvironmentToolset
from google.adk.environment import LocalEnvironment
from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor

# エージェントのあるディレクトリパスを取得します。
current_dir = pathlib.Path(__file__).parent

# 「skill-generator」スキルをロードします。
skill_generator_skill = load_skill_from_dir(
    current_dir / "skills" / "skill-generator"
)


# 「skill-manager」スキルをロードします。
skill_manager_skill = load_skill_from_dir(
    current_dir / "skills" / "skill-manager"
)

# 「trigger-evaluator」スキルをロードします。
trigger_evaluator_skill = load_skill_from_dir(
    current_dir / "skills" / "trigger-evaluator"
)

# Google ADK 2.0 に準拠したエージェントを定義します。
# 読み込んだスキルと、それを動作させるためのローカル実行環境（EnvironmentToolset）を登録します。
import os
is_eval_mode = os.environ.get("ADK_EVAL_MODE") == "1"

agent_tools = [
    # スキルをロードするためのツールセット
    skill_toolset.SkillToolset(
        skills=[skill_generator_skill, skill_manager_skill, trigger_evaluator_skill],
        code_executor=UnsafeLocalCodeExecutor()
    )
]

if not is_eval_mode:
    # スクリプトをローカルシェル経由で実行するためのツールセット
    agent_tools.append(EnvironmentToolset(environment=LocalEnvironment()))

root_agent = Agent(
    model='gemini-2.5-flash',
    name='evaluation_driven_development_agent',
    instruction=(
        "あなたは自立的評価駆動開発エージェントです。\n"
        "ユーザーから新しいスキルやアセットの生成、あるいは機能開発の指示を受けた場合、自身に登録されている `skill-generator` スキルを活用して、自律的に新しいスキルを生成してください。\n"
        "また、生成されたスキルのTierや権限ポリシーは、登録されている `skill-manager` スキルを使用して管理してください。\n"
        "さらに、スキルのトリガー定義の品質および実際のトリガー精度は、登録されている `trigger-evaluator` スキルを用いて評価してください。\n"
        "\n"
        "スキル生成を行う手順：\n"
        "1. ローカル環境のシェル経由（`EnvironmentToolset`）で、`src/skills/skill-generator/scripts/generate_skill.py` を実行します。\n"
        "2. コマンドライン引数には以下を指定してください：\n"
        "   - `--output_dir`: 生成するスキルの出力先（通常は `src/skills/[スキル名]`）\n"
        "   - `--prompt`: ユーザーが求めるスキルの詳細な要件や説明\n"
        "3. スクリプトの実行例：\n"
        "   `python src/skills/skill-generator/scripts/generate_skill.py --output_dir src/skills/my-new-skill --prompt \"要件\"`\n"
        "4. `generate_skill.py` は、内部でテストデータセットの作成、および `adk eval run` による評価駆動のテスト・自己修復ループを自動で実行します。テストが正常に通過し、スキルが完全に生成されるのを確認してから、ユーザーに報告してください。"
    ),
    tools=agent_tools
)
