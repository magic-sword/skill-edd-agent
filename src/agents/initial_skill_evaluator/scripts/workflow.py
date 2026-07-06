"""
initial_skill_evaluator の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠。
推論が必要なステップは LLMエージェント、
機械的な処理（登録・テスト実行・Tier更新）は Python関数ノードで直接実行します。
"""
from google.adk import Workflow
from google.adk import Agent
from google.adk.workflow import node
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState

DEFAULT_MODEL = "gemini-2.5-flash"

# スキル状態管理の初期化
state = SkillsState()


# ==========================================
# 1. Python関数ノードの定義
# ==========================================

@node(name="register_skill_node")
def register_skill_node(tool_context: ToolContext):
    """評価対象のスキルを登録コマンドにかけます（Tier 0は自動スキップされます）。"""
    handler = state.get_skill("skill-manager").load_module()
    
    # パラメータオブジェクトを構築
    params = handler.Input(
        command="register",
        skill=tool_context.state.get("skill"),
        tier=0
    )
    
    # 実行
    handler.process_message(params, tool_context)


@node(name="run_trigger_tests_node")
def run_trigger_tests_node(tool_context: ToolContext):
    """トリガーテストケースの実行を行います。"""
    handler = state.get_skill("mock-executor").load_module()
    
    params = handler.Input(
        skill=tool_context.state.get("skill"),
        eval_set_path=tool_context.state.get("trig_eval_set_path"),
        threshold_accuracy=0.90
    )
    
    handler.process_message(params, tool_context)


@node(name="run_unit_tests_node")
def run_unit_tests_node(tool_context: ToolContext):
    """ユニットテストの実行を行います。"""
    handler = state.get_skill("test-executor").load_module()
    
    params = handler.Input(
        skill=tool_context.state.get("skill"),
        eval_set_path=tool_context.state.get("eval_set_path"),
        threshold_accuracy=1.00
    )
    
    handler.process_message(params, tool_context)


@node(name="set_skill_tier_node")
def set_skill_tier_node(tool_context: ToolContext):
    """評価結果が合格であれば、スキルのTierを1に更新します。"""
    handler = state.get_skill("skill-manager").load_module()
    
    params = handler.Input(
        command="set-tier",
        skill=tool_context.state.get("skill"),
        tier=1
    )
    
    handler.process_message(params, tool_context)


# ==========================================
# 2. LLMエージェントの定義 (推論・生成を伴うステップ)
# ==========================================

generate_trigger_tests_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_trigger_tests_agent",
    tools=[state.get_skill("trigger-evaluator").get_tool()],
    instruction="登録したスキルのトリガーテストケースを自動生成してください。ユーザーに対するテキスト応答メッセージは一切出力せず、サイレントに完了してください。"
)

generate_unit_tests_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_unit_tests_agent",
    tools=[state.get_skill("eval-unit-tester").get_tool()],
    instruction="評価対象スキルのユニットテストケースを自動生成してください。ユーザーに対するテキスト応答メッセージは一切出力せず、サイレントに完了してください。"
)


# ==========================================
# 3. ワークフローの定義と接続
# ==========================================
root_workflow = Workflow(
    name="initial_skill_evaluator",
    edges=[
        ("START", register_skill_node),
        (register_skill_node, generate_trigger_tests_agent),
        (generate_trigger_tests_agent, run_trigger_tests_node),
        (run_trigger_tests_node, generate_unit_tests_agent),
        (generate_unit_tests_agent, run_unit_tests_node),
        (run_unit_tests_node, set_skill_tier_node),
    ]
)
