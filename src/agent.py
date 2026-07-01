"""
A2Aプロトコル互換の自立的評価駆動開発エージェントのコア定義。
"""
import pathlib
import os
import sys
from google.adk import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset
from google.adk.tools.environment import EnvironmentToolset
from google.adk.environment import LocalEnvironment
from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor

# エージェントのあるディレクトリパスを取得します。
current_dir = pathlib.Path(__file__).parent
skills_dir = current_dir / "skills"

# 評価モードの時は、開発サイクル用システムスキルおよび評価対象外のスキルを排除してツール混同を防ぎます
is_eval_mode = os.environ.get("ADK_EVAL_MODE") == "1"
system_skills = {"skill-generator", "skill-manager", "trigger-evaluator", "eval-unit-tester", "test-executor"}

target_eval_skill = None
if is_eval_mode:
    # コマンドライン引数 (sys.argv) から現在評価中のスキル名を特定する
    for arg in sys.argv:
        if "skills/" in arg:
            parts = arg.split("skills/")
            if len(parts) > 1:
                skill_name = parts[1].split("/")[0]
                target_eval_skill = skill_name
                break

# skills ディレクトリ配下のすべてのスキルフォルダを動的にロードします。
loaded_skills = []
if skills_dir.exists():
    for skill_path in skills_dir.iterdir():
        if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
            skill_name = skill_path.name
            if is_eval_mode:
                if skill_name in system_skills:
                    continue # システム開発スキルを排除
                if target_eval_skill and skill_name != target_eval_skill:
                    continue # 評価対象外の別スキルを排除して混同を防ぐ
            try:
                skill = load_skill_from_dir(skill_path)
                loaded_skills.append(skill)
            except Exception as e:
                print(f"Warning: Failed to load skill from {skill_path}: {e}", file=sys.stderr)

# Google ADK 2.0 に準拠したエージェントを定義します。
agent_tools = [
    # スキルをロードするためのツールセット
    skill_toolset.SkillToolset(
        skills=loaded_skills,
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
        "ユーザーから新しいスキルやアセットの生成、あるいは機能開発の指示を受けた場合、以下のワークフローに従って開発、テスト生成、テスト実行、Tier管理を自律的に行ってください。\n"
        "\n"
        "【スキル開発および昇格（Tier 2）ワークフロー】\n"
        "1. スキル生成の実行:\n"
        "   `EnvironmentToolset`（シェル実行）または該当ツールを用いて、`skill-generator` を動かします。\n"
        "   `python src/skills/skill-generator/scripts/generate_skill.py --output_dir src/skills/[スキル名] --prompt \"[要件]\"`\n"
        "   これにより、スキルの本体コードと仕様書が作成されます。\n"
        "2. 単体テストケースの生成:\n"
        "   `eval-unit-tester` を実行し、生成したスキルに対する unit test アセット（*.evalset.json）を自動生成させます。\n"
        "   `python src/skills/eval-unit-tester/scripts/eval_unit_tester.py --skill_name [スキル名]`\n"
        "3. テストの実行（タイムアウト保護付き）:\n"
        "   `test-executor` を実行し、生成された単体テストケースが100%合格するか確認します。\n"
        "   `python src/skills/test-executor/scripts/execute_test.py --skill_name [スキル名] --eval_set_path src/skills/[スキル名]/tests/[スキル名]_eval_set.evalset.json --threshold_accuracy 1.0`\n"
        "4. Tierの昇格:\n"
        "   テストが 100% 合格したら、`skill-manager` を用いて対象スキルを Tier 2 (Draft-Only) に昇格させます。\n"
        "   `python src/skills/skill-manager/scripts/manage_skills.py set-tier [スキル名] 2`\n"
        "\n"
        "【トリガー品質評価（Tier 3）ワークフロー】\n"
        "1. トリガーテストケースの生成:\n"
        "   `trigger-evaluator` を実行し、静的チェックを行うと共に陽性・陰性プロンプト（20件）のテストアセットを自動生成させます。\n"
        "   `python src/skills/trigger-evaluator/scripts/evaluate_trigger.py --skill_name [スキル名]`\n"
        "2. テストの実行（合格閾値 90%）:\n"
        "   `test-executor` を実行し、トリガー精度が 90% 以上であることを確認します。\n"
        "   `python src/skills/test-executor/scripts/execute_test.py --skill_name [スキル名] --eval_set_path src/skills/[スキル名]/tests/[スキル名]_trigger_eval.evalset.json --threshold_accuracy 0.90`\n"
        "3. メタデータの更新:\n"
        "   合格した場合、`skill-manager` を用いて対象スキルのトリガー評価ステータスと精度を同期・更新します。\n"
        "   `python src/skills/skill-manager/scripts/manage_skills.py update-trigger [スキル名] --accuracy [スコア] --status PASSED`"
    ),
    tools=agent_tools
)
