"""
generate-skill-workflow の Workflow オブジェクト定義。
ADK 2.0 の「ToolContext ＆ 共有セッション状態」に準拠し、
状態バケツリレー用の WorkflowState スキーマや LLM Agent に対する JSON 制御指示を完全に排除する。
各エージェントはインプロセス関数ツール (FunctionTool) を実行し、状態は ToolContext を介して裏側で自動的に共有される。
"""
import importlib.util
import sys
import os
from google.adk import Workflow
from google.adk import Agent
from google.adk.tools import FunctionTool

DEFAULT_MODEL = "gemini-2.5-flash"

def import_function_from_path(module_name: str, file_path: str, function_name: str):
    """
    ハイフンを含むパスでもインポートできるよう、ファイル絶対パスから動的に関数をロードします。
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Script file not found: {abs_path}")
    spec = importlib.util.spec_from_file_location(module_name, abs_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return getattr(module, function_name)

# インプロセスツールの関数を動的ロード
set_skill_tier = import_function_from_path(
    "manage_skills",
    "/workspace/src/skills/skill-manager/scripts/manage_skills.py",
    "set_skill_tier"
)

generate_skill_code = import_function_from_path(
    "generate_skill",
    "/workspace/src/skills/skill-generator/scripts/generate_skill.py",
    "generate_skill_code"
)

generate_unit_tests = import_function_from_path(
    "eval_unit_tester",
    "/workspace/src/skills/eval-unit-tester/scripts/eval_unit_tester.py",
    "generate_unit_tests"
)

run_skill_tests = import_function_from_path(
    "execute_test",
    "/workspace/src/skills/test-executor/scripts/execute_test.py",
    "run_skill_tests"
)

generate_trigger_tests = import_function_from_path(
    "evaluate_trigger",
    "/workspace/src/skills/trigger-evaluator/scripts/evaluate_trigger.py",
    "generate_trigger_tests"
)


# ==========================================
# 各ステップ専用エージェント（ノード）の定義
# ==========================================

# ステップ1: スキル仮登録エージェント (Tier 0)
set_tier_0_agent = Agent(
    model=DEFAULT_MODEL,
    name="set_tier_0_agent",
    tools=[FunctionTool(func=set_skill_tier)],
    instruction=(
        "あなたはスキル登録の担当者です。`set_skill_tier` ツールを呼び出して、"
        "現在のスキルを Tier 0 (試験中) で仮登録してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- command: 'set-tier'\n"
        "- tier: 0"
    )
)

# ステップ2: スキル本体コード生成エージェント
generate_skill_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_skill_agent",
    tools=[FunctionTool(func=generate_skill_code)],
    instruction=(
        "あなたはスキル開発の担当者です。`generate_skill_code` ツールを呼び出して、"
        "新規スキルの本体コードの自動生成を実行してください。\n"
        "要件（temp:prompt）はセッション状態に設定されています。引数は不要です。"
    )
)

# ステップ3: 単体テストケース生成エージェント
generate_unit_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_unit_test_agent",
    tools=[FunctionTool(func=generate_unit_tests)],
    instruction=(
        "あなたは単体テストアセットの生成担当者です。`generate_unit_tests` ツールを呼び出して、"
        "現在のスキルに対する単体テストケースの自動生成を実行してください。\n"
        "引数は不要です。"
    )
)

# ステップ4: 単体テスト実行エージェント（精度100%必須）
execute_unit_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="execute_unit_test_agent",
    tools=[FunctionTool(func=run_skill_tests)],
    instruction=(
        "あなたは単体テスト実行の担当者です。`run_skill_tests` ツールを呼び出して、"
        "生成された単体テストケースを実行し合格判定を行ってください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- eval_mode: 1 (単体評価用)\n"
        "- threshold_accuracy: 1.0"
    )
)

# ステップ5: トリガーテストケース生成エージェント
generate_trigger_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_trigger_test_agent",
    tools=[FunctionTool(func=generate_trigger_tests)],
    instruction=(
        "あなたはトリガー精度テストケースの生成担当者です。`generate_trigger_tests` ツールを呼び出して、"
        "現在のスキルに対するトリガー精度テストケースの自動生成を実行してください。\n"
        "引数は不要です。"
    )
)

# ステップ6: トリガーテスト実行エージェント（精度90%必須）
execute_trigger_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="execute_trigger_test_agent",
    tools=[FunctionTool(func=run_skill_tests)],
    instruction=(
        "あなたはトリガー精度テスト実行の担当者です。`run_skill_tests` ツールを呼び出して、"
        "生成されたトリガーテストケースを実行し合格判定を行ってください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- eval_mode: 0 (トリガー評価用)\n"
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
    name="generate_skill_workflow",
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
