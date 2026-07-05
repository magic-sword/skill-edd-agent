"""
skill_developer の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠し、
各エージェントは統一プロセス機能ツール (FunctionTool) を実行し、状態は ToolContext を介して自動的に共有されます。
"""
from google.adk import Workflow
from google.adk import Agent
from edd_agent_tools.registry import SkillRegistry

DEFAULT_MODEL = "gemini-2.5-flash"

# レジストリを初期化
registry = SkillRegistry()

# 統一ハンドラー経由のツールロード
skill_manager_tool = registry.get_tools(["skill-manager"])[0]
skill_generator_tool = registry.get_tools(["skill-generator"])[0]
eval_unit_tester_tool = registry.get_tools(["eval-unit-tester"])[0]
test_executor_tool = registry.get_tools(["test-executor"])[0]
trigger_evaluator_tool = registry.get_tools(["trigger-evaluator"])[0]
mock_executor_tool = registry.get_tools(["mock-executor"])[0]

# ==========================================
# 各ステップ専用エージェント（ノード）の定義
# ==========================================

# ステップ1: スキル仮登録エージェント (Tier 0)
set_tier_0_agent = Agent(
    model=DEFAULT_MODEL,
    name="set_tier_0_agent",
    tools=[skill_manager_tool],
    instruction=(
        "あなたはスキル登録の担当者です。`skill_manager` ツールを呼び出して、"
        "現在のスキルを Tier 0 (試験中) で仮登録してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- command: 'register'\n"
        "- skill: (開発対象のスキル名)"
    )
)

# ステップ2: スキル本体コード生成エージェント
generate_skill_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_skill_agent",
    tools=[skill_generator_tool],
    instruction=(
        "あなたはスキル開発の担当者です。`skill_generator` ツールを呼び出して、"
        "新規スキルの本体コードの自動生成を実行してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- skill: (開発対象のスキル名)\n"
        "- prompt: (セッション状態から得られる機能要件)"
    )
)

# ステップ3: 単体テストケース生成エージェント
generate_unit_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_unit_test_agent",
    tools=[eval_unit_tester_tool],
    instruction=(
        "あなたは単体テストアセットの生成担当者です。`eval_unit_tester` ツールを呼び出して、"
        "現在のスキルに対する単体テストケースの自動生成を実行してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- skill: (開発対象のスキル名)"
    )
)

# ステップ4: 単体テスト実行エージェント（精度100%必須）
execute_unit_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="execute_unit_test_agent",
    tools=[test_executor_tool],
    instruction=(
        "あなたは単体テスト実行の担当者です。`test_executor` ツールを呼び出して、"
        "生成された単体テストケースを実行し合格判定を行ってください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- skill: (開発対象のスキル名)\n"
        "- eval_set_path: (単体テストファイルへの絶対パス。通常 `tests/unit_test_cases.evalset.json`)\n"
        "- threshold_accuracy: 1.0"
    )
)

# ステップ5: トリガーテストケース生成エージェント
generate_trigger_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_trigger_test_agent",
    tools=[trigger_evaluator_tool],
    instruction=(
        "あなたはトリガー精度テストケースの生成担当者です。`trigger_evaluator` ツールを呼び出して、"
        "現在のスキルに対するトリガー精度テストケースの自動生成を実行してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- skill: (開発対象のスキル名)"
    )
)

# ステップ6: トリガーテスト実行エージェント（精度90%必須）
execute_trigger_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="execute_trigger_test_agent",
    tools=[mock_executor_tool],
    instruction=(
        "あなたはトリガー精度テスト実行の担当者です。`mock_executor` ツールを呼び出して、"
        "生成されたトリガーテストケースを実行し合格判定を行ってください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- skill: (開発対象のスキル名)\n"
        "- eval_set_path: (トリガーテストファイルへの絶対パス。通常 `tests/trigger_test_cases.evalset.json`)\n"
        "- threshold_accuracy: 0.90"
    )
)

# ステップ7: スキル正式本登録エージェント (Tier 1 & クリーンアップ)
set_tier_1_agent = Agent(
    model=DEFAULT_MODEL,
    name="set_tier_1_agent",
    tools=[FunctionTool(func=set_skill_tier)],
    instruction=(
        "あなたはスキル正式本登録の担当者です。`set_skill_tier` ツールを呼び出して、"
        "現在のスキルを Tier 1 に本登録してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- command: 'set-tier'\n"
        "- tier: 1"
    )
)

# ==========================================
# ワークフローの定義と接続
# ==========================================
root_workflow = Workflow(
    name="skill_developer",
    edges=[
        ("START", set_tier_0_agent),
        (set_tier_0_agent, generate_skill_agent),
        (generate_skill_agent, generate_unit_test_agent),
        (generate_unit_test_agent, execute_unit_test_agent),
        (execute_unit_test_agent, generate_trigger_test_agent),
        (generate_trigger_test_agent, execute_trigger_test_agent),
        (execute_trigger_test_agent, set_tier_1_agent),
    ]
)
