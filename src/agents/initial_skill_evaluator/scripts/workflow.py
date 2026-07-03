"""
initial_skill_evaluator の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠。
各エージェントはインプロセス関数ツール (FunctionTool) を実行し、状態は ToolContext を介して裏側で自動的に共有されます。
"""
from google.adk import Workflow
from google.adk import Agent
from google.adk.tools import FunctionTool
from edd_agent_tools.registry import SkillRegistry

DEFAULT_MODEL = "gemini-2.5-flash"

# レジストリを初期化してインプロセスツールの関数を動的ロード
registry = SkillRegistry()

# 依存するスキルからツールを動的ロード
set_skill_tier = registry.load_tool("skill-manager", "set_skill_tier")
generate_trigger_tests = registry.load_tool("trigger-evaluator", "generate_trigger_tests")
run_skill_tests = registry.load_tool("test-executor", "run_skill_tests")
generate_unit_tests = registry.load_tool("eval-unit-tester", "generate_unit_tests")


# ==========================================
# 各ステップ専用エージェント（ノード）の定義
# ==========================================

# 各エージェント（ノード）の定義
register_skill_agent = Agent(
    model=DEFAULT_MODEL,
    name="register_skill_agent",
    tools=[FunctionTool(func=set_skill_tier)],
    instruction="ToolContext から 'skill_name' と 'skill_id' を取得し、それらを引数として command='register', tier=0 で set_skill_tier 関数を実行します。"
)

generate_trigger_tests_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_trigger_tests_agent",
    tools=[FunctionTool(func=generate_trigger_tests)],
    instruction="ToolContext から 'skill_name' と 'skill_id' を取得し、それらを引数として generate_trigger_tests 関数を実行します。"
)

run_trigger_tests_agent = Agent(
    model=DEFAULT_MODEL,
    name="run_trigger_tests_agent",
    tools=[FunctionTool(func=run_skill_tests)],
    instruction="ToolContext から 'skill_name' と 'skill_id' を取得し、それらを引数として eval_mode=0, threshold_accuracy=0.90 で run_skill_tests 関数を実行します。"
)

generate_unit_tests_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_unit_tests_agent",
    tools=[FunctionTool(func=generate_unit_tests)],
    instruction="ToolContext から 'skill_name' と 'skill_id' を取得し、それらを引数として generate_unit_tests 関数を実行します。"
)

run_unit_tests_agent = Agent(
    model=DEFAULT_MODEL,
    name="run_unit_tests_agent",
    tools=[FunctionTool(func=run_skill_tests)],
    instruction="ToolContext から 'skill_name' と 'skill_id' を取得し、それらを引数として eval_mode=1, threshold_accuracy=1.0 で run_skill_tests 関数を実行します。"
)

set_skill_tier_agent = Agent(
    model=DEFAULT_MODEL,
    name="set_skill_tier_agent",
    tools=[FunctionTool(func=set_skill_tier)],
    instruction="ToolContext から 'skill_name' と 'skill_id' を取得し、それらを引数として command='set-tier', tier=1 で set_skill_tier 関数を実行します。"
)


# ==========================================
# ワークフローの定義と接続
# ==========================================
root_workflow = Workflow(
    name="initial_skill_evaluator",
    edges=[
        ("START", register_skill_agent),
        (register_skill_agent, generate_trigger_tests_agent),
        (generate_trigger_tests_agent, run_trigger_tests_agent),
        (run_trigger_tests_agent, generate_unit_tests_agent),
        (generate_unit_tests_agent, run_unit_tests_agent),
        (run_unit_tests_agent, set_skill_tier_agent),
        (set_skill_tier_agent, "END"),
    ]
)
