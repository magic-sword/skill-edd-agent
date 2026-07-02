"""
Google ADK 2.0 に準拠した、エージェントノードによるスキル生成・テスト・本登録の抽象DAGワークフロー定義。
すべてのノードは共通の Pydantic 状態スキーマ (WorkflowState) をバインドし、型安全な Structured Outputs で連携します。
"""
import os
import pathlib
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from google.adk import Workflow
from google.adk.agents import Agent
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor
from google.adk.skills import load_skill_from_dir

WORKSPACE_ROOT = "/workspace"
DEFAULT_MODEL = "gemini-2.5-flash"

def create_skill_toolset(skill_name: str) -> SkillToolset:
    """
    指定されたスキルのみをロードした専用の SkillToolset を生成します。
    """
    skill_path = pathlib.Path(WORKSPACE_ROOT) / "src" / "skills" / skill_name
    skill = load_skill_from_dir(skill_path)
    return SkillToolset(
        skills=[skill],
        code_executor=UnsafeLocalCodeExecutor()
    )

# ==========================================
# ワークフロー共有状態 (WorkflowState) の定義
# ==========================================
class WorkflowState(BaseModel):
    skill_name: str = Field(description="作成・管理するスキルの名前（ケバブケース）")
    prompt: str = Field(description="作成するスキルの仕様・要件プロンプト")
    registry_path: str = Field(default="/workspace/src/skills_registry.json", description="registryファイルの絶対パス")
    
    # 各エージェントが順次書き出していく成果物のパス
    reg_out_json_path: Optional[str] = Field(default=None, description="仮登録結果JSONファイルの絶対パス")
    skill_dir: Optional[str] = Field(default=None, description="生成されたスキルの絶対ディレクトリパス")
    eval_set_path: Optional[str] = Field(default=None, description="生成された単体テストアセットJSON of 絶対パス")
    trig_eval_set_path: Optional[str] = Field(default=None, description="生成されたトリガーテストアセットJSONの絶対パス")
    
    status: str = Field(default="success", description="現在の処理ステータス ('success' または 'failed')")
    message: str = Field(default="", description="付加的な進捗メッセージやエラー詳細")

    @model_validator(mode="after")
    def check_status(self) -> 'WorkflowState':
        if self.status == "failed":
            raise ValueError(f"【ワークフロー自動中断】処理が失敗しました: {self.message}")
        return self

# ==========================================
# 各ステップ専用エージェント（ノード）の定義
# ==========================================

# ステップ1: スキル仮登録エージェント (Tier 0)
set_tier_0_agent = Agent(
    model=DEFAULT_MODEL,
    name="set_tier_0_agent",
    tools=[create_skill_toolset("skill-manager")],
    input_schema=WorkflowState,
    output_schema=WorkflowState,
    instruction=(
        "あなたはスキル登録の担当者です。入力された状態から skill_name と registry_path を取得し、"
        "run_skill_script ツールを使って 'manage_skills.py' を実行してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- command: 'set-tier'\n"
        "- skill_name: <状態の skill_name>\n"
        "- tier: 0\n"
        "- registry_path: <状態の registry_path>\n"
        "- output_json: '/workspace/src/.workflow_tmp/<skill_name>/01_reg_out.json'\n"
        "実行完了後、得られた出力ファイルパスを reg_out_json_path フィールドにセットして、状態を返してください。"
    )
)

# ステップ2: スキル本体コード生成エージェント
generate_skill_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_skill_agent",
    tools=[create_skill_toolset("skill-generator")],
    input_schema=WorkflowState,
    output_schema=WorkflowState,
    instruction=(
        "あなたはスキル生成の担当者です。入力された prompt を取得し、"
        "run_skill_script ツールを使って 'generate_skill.py' を実行してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- output_dir: 'src/skills/<状態の skill_name>'\n"
        "- prompt: <状態の prompt>\n"
        "- output_json: '/workspace/src/.workflow_tmp/<skill_name>/02_gen_out.json'\n"
        "実行完了後、生成されたディレクトリ絶対パス '/workspace/src/skills/<skill_name>' を skill_dir フィールドにセットして、状態を返してください。"
    )
)

# ステップ3: 単体テストケース生成エージェント
generate_unit_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_unit_test_agent",
    tools=[create_skill_toolset("eval-unit-tester")],
    input_schema=WorkflowState,
    output_schema=WorkflowState,
    instruction=(
        "あなたは単体テストアセットの生成担当者です。入力された skill_name を取得し、"
        "run_skill_script ツールを使って 'eval_unit_tester.py' を実行してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- skill_name: <状態の skill_name>\n"
        "- output_json: '/workspace/src/.workflow_tmp/<skill_name>/03_ut_gen_out.json'\n"
        "実行完了後、生成されたテストアセットJSONの絶対パス（例: '/workspace/src/skills/<skill_name>/tests/<skill_name_with_underscores>_eval_set.evalset.json'）を eval_set_path フィールドにセットして、状態を返してください。"
    )
)

# ステップ4: 単体テスト実行エージェント（精度100%必須）
execute_unit_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="execute_unit_test_agent",
    tools=[create_skill_toolset("test-executor")],
    input_schema=WorkflowState,
    output_schema=WorkflowState,
    instruction=(
        "あなたは単体テスト実行の担当者です。入力された skill_name と eval_set_path を取得し、"
        "run_skill_script ツールを使って 'execute_test.py' を実行してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- skill_name: <状態の skill_name>\n"
        "- eval_set_path: <状態の eval_set_path>\n"
        "- threshold_accuracy: 1.0\n"
        "- eval_mode: 1\n"
        "- output_json: '/workspace/src/.workflow_tmp/<skill_name>/04_ut_exec_out.json'\n"
        "テストが合格（精度 1.0）した場合は、状態をそのまま返してください。\n"
        "もし不合格の場合は、statusフィールドを 'failed' にし、メッセージを記録して即座に異常終了させてください。"
    )
)

# ステップ5: トリガーテストケース生成エージェント
generate_trigger_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="generate_trigger_test_agent",
    tools=[create_skill_toolset("trigger-evaluator")],
    input_schema=WorkflowState,
    output_schema=WorkflowState,
    instruction=(
        "あなたはトリガー精度テストケースの生成担当者です。入力された skill_name を取得し、"
        "run_skill_script ツールを使って 'evaluate_trigger.py' を実行してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- skill_name: <状態の skill_name>\n"
        "- output_json: '/workspace/src/.workflow_tmp/<skill_name>/05_trig_gen_out.json'\n"
        "実行完了後、生成されたトリガーテストアセットJSONの絶対パス（例: '/workspace/src/skills/<skill_name>/tests/<skill_name>_trigger_eval.evalset.json'）を trig_eval_set_path フィールドにセットして、状態を返してください。"
    )
)

# ステップ6: トリガーテスト実行エージェント（精度90%必須）
execute_trigger_test_agent = Agent(
    model=DEFAULT_MODEL,
    name="execute_trigger_test_agent",
    tools=[create_skill_toolset("test-executor")],
    input_schema=WorkflowState,
    output_schema=WorkflowState,
    instruction=(
        "あなたはトリガー精度テスト実行の担当者です。入力された skill_name と trig_eval_set_path を取得し、"
        "run_skill_script ツールを使って 'execute_test.py' を実行してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- skill_name: <状態の skill_name>\n"
        "- eval_set_path: <状態の trig_eval_set_path>\n"
        "- threshold_accuracy: 0.90\n"
        "- eval_mode: 0\n"
        "- output_json: '/workspace/src/.workflow_tmp/<skill_name>/06_trig_exec_out.json'\n"
        "テストが合格（精度 0.90以上）した場合は、状態をそのまま返してください。\n"
        "もし不合格の場合は、statusフィールドを 'failed' にし、メッセージを記録して即座に異常終了させてください。"
    )
)

# ステップ7: スキル正式本登録エージェント (Tier 1 & クリーンアップ)
set_tier_1_agent = Agent(
    model=DEFAULT_MODEL,
    name="set_tier_1_agent",
    tools=[create_skill_toolset("skill-manager")],
    input_schema=WorkflowState,
    output_schema=WorkflowState,
    instruction=(
        "あなたはスキル正式本登録の担当者です。入力された skill_name と registry_path を取得し、“"
        "run_skill_script ツールを使って 'manage_skills.py' を実行してください。\n"
        "【ツール呼び出しパラメータ】\n"
        "- command: 'set-tier'\n"
        "- skill_name: <状態の skill_name>\n"
        "- tier: 1\n"
        "- registry_path: <状態の registry_path>\n"
        "- output_json: '/workspace/src/.workflow_tmp/<skill_name>/07_final_reg_out.json'\n"
        "本登録完了後、一時作業ディレクトリ '/workspace/src/.workflow_tmp/<skill_name>' を完全に削除し、クリーンアップを行ってください。\n"
        "最後に、最終結果として status='success', message='Workflow successfully completed.' をセットして状態を返却してください。"
    )
)

# ==========================================
# 静的グラフ（Workflow）の定義と接続
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
