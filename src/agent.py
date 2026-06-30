"""
A2Aプロトコル互換の自立的評価駆動開発エージェントのコア定義。
"""
import pathlib
import sys
sys.modules.pop('google', None)
sys.modules.pop('google.adk', None)
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

# Google ADK 2.0 に準拠したエージェントを定義します。
# 読み込んだスキルと、それを動作させるためのローカル実行環境（EnvironmentToolset）を登録します。
root_agent = Agent(
    model='gemini-2.5-flash',
    name='evaluation_driven_development_agent',
    instruction=(
        "あなたは自立的評価駆動開発エージェントです。\n"
        "ユーザーから新しいスキルやアセットの生成、あるいは機能開発の指示を受けた場合、自身に登録されている `skill-generator` スキルを活用して、自律的に新しいスキルを生成してください。\n"
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
    tools=[
        # スキルをロードするためのツールセット
        skill_toolset.SkillToolset(
            skills=[skill_generator_skill],
            code_executor=UnsafeLocalCodeExecutor()
        ),
        # スクリプトをローカルシェル経由で実行するためのツールセット
        EnvironmentToolset(environment=LocalEnvironment())
    ]
)
