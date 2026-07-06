"""
skill-developer の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠。
"""
from google.adk import Workflow
from google.adk import Agent
from google.adk.tools import FunctionTool
from edd_agent_tools.skills import SkillsState

DEFAULT_MODEL = "gemini-2.5-flash"

state = SkillsState()

# 依存するスキルからツールをロードし、各ステップのエージェント(ノード)を定義
# skill-designer
skill_designer = state.get_skill("skill-designer")
tool_designer = skill_designer.get_tool()
step_designer_agent = Agent(
    model=DEFAULT_MODEL,
    name="skill_designer_agent",
    tools=[tool_designer],
    instruction=(
        '''あなたはスキルの設計を担当するエージェントです。
ユーザーの要求と初期入力として与えられたプロンプトに基づいて skill-designer ツールを呼び出し、スキル設計を行います。
設計結果として design.json のパスをセッション状態に保存してください。'''
    )
)

# skill-coder
skill_coder = state.get_skill("skill-coder")
tool_coder = skill_coder.get_tool()
step_coder_agent = Agent(
    model=DEFAULT_MODEL,
    name="skill_coder_agent",
    tools=[tool_coder],
    instruction=(
        '''あなたはスキルの実装を担当するエージェントです。
前のステップで生成された design.json のパスと、出力先ディレクトリがセッション状態にあります。
これらの情報に基づいて skill-coder ツールを呼び出し、実装コードを生成してください。
実装コードの出力先ディレクトリ（source_code_dir）をセッション状態に保存してください。'''
    )
)

# skill-spec-writer
skill_spec_writer = state.get_skill("skill-spec-writer")
tool_spec_writer = skill_spec_writer.get_tool()
step_spec_writer_agent = Agent(
    model=DEFAULT_MODEL,
    name="skill_spec_writer_agent",
    tools=[tool_spec_writer],
    instruction=(
        '''あなたはスキル仕様書の生成を担当するエージェントです。
前のステップで生成された design.json のパスとソースコードのディレクトリがセッション状態にあります。
これらの情報に基づいて skill-spec-writer ツールを呼び出し、スキル仕様書（SKILL.md）を生成します。
生成された SKILL.md の絶対パス（output_file_path）をセッション状態に保存してください。これが最終的なワークフローの出力となります。'''
    )
)

# ==========================================
# ワークフローの定義と接続
# ==========================================
root_workflow = Workflow(
    name="skill_developer",
    edges=[
        ("START", step_designer_agent),
        (step_designer_agent, step_coder_agent),
        (step_coder_agent, step_spec_writer_agent)
    ]
)
