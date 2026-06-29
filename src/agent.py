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

# エージェントのあるディレクトリパスを取得します。
current_dir = pathlib.Path(__file__).parent

# 「file-processor」スキルをローカルディレクトリからロードします。
file_processor_skill = load_skill_from_dir(
    current_dir / "skills" / "file-processor"
)

# 「skill-generator」スキルをロードします。
skill_generator_skill = load_skill_from_dir(
    current_dir / "skills" / "skill-generator"
)

# Google ADK 2.0 に準拠したエージェントを定義します。
# 読み込んだスキルと、それを動作させるためのローカル実行環境（EnvironmentToolset）を登録します。
root_agent = Agent(
    model='gemini-2.0-flash',
    name='evaluation_driven_development_agent',
    instruction=(
        "あなたは自立的評価駆動開発エージェントです。\n"
        "ユーザーの指示に従い、評価駆動でスキルを開発・統合する能力を持ちます。\n"
        "必要に応じて、登録されたスキル内のスクリプトを実行し、ファイルを操作してください。"
    ),
    tools=[
        # スキルをロードするためのツールセット
        skill_toolset.SkillToolset(skills=[file_processor_skill, skill_generator_skill]),
        # スクリプトをローカルシェル経由で実行するためのツールセット
        EnvironmentToolset(environment=LocalEnvironment())
    ]
)
