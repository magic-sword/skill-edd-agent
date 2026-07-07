from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
import json

def run_evaluate_and_register_skill_step(tool_context: ToolContext) -> str:
    """
    各検証ステップの結果を評価し、すべて成功していれば対象スキルをTier 1として登録します。
    失敗した場合はその詳細を収集します。
    """
    # tool_context.state から各ステップの結果を取得
    trigger_evaluator_result = tool_context.state.get("trigger_evaluator_result", {})
    test_executor_result = tool_context.state.get("test_executor_result", {})
    import_validator_result = tool_context.state.get("import_validator_result", {})
    design_validator_result = tool_context.state.get("design_validator_result", {})

    all_successful = True
    failed_steps_details = []

    # 各ステップの結果を評価
    # trigger-evaluator
    if trigger_evaluator_result.get("status") != "success":
        all_successful = False
        failed_steps_details.append(
            f"- Trigger Evaluator: {trigger_evaluator_result.get('message', '詳細不明')}"
        )

    # test-executor
    # threshold_accuracy を考慮する必要がある
    threshold_accuracy = tool_context.get_parameter("threshold_accuracy", 1.0)
    test_accuracy = test_executor_result.get("accuracy", 0.0) # test-executor の結果に accuracy があることを期待
    if test_executor_result.get("status") != "success" or test_accuracy < threshold_accuracy:
        all_successful = False
        failed_steps_details.append(
            f"- Test Executor: {test_executor_result.get('message', '詳細不明')} (Accuracy: {test_accuracy}, Threshold: {threshold_accuracy})"
        )

    # import-validator
    if import_validator_result.get("status") != "success":
        all_successful = False
        failed_steps_details.append(
            f"- Import Validator: {import_validator_result.get('message', '詳細不明')}"
        )

    # design-validator
    if design_validator_result.get("status") != "success":
        all_successful = False
        failed_steps_details.append(
            f"- Design Validator: {design_validator_result.get('message', '詳細不明')}"
        )

    registered = False
    message = ""
    status = "failed"

    if all_successful:
        try:
            skill_name_to_register = tool_context.get_parameter("skill")
            skills_state = SkillsState()
            skills_state.load()
            # Tier 1 は設計定義により READ_ONLY と指定
            skills_state.promote_skill(skill_name_to_register, "READ_ONLY")
            skills_state.save() # 変更を保存

            message = f"すべての検証ステップが成功しました。スキル '{skill_name_to_register}' がTier 1（READ_ONLY）として登録されました。"
            registered = True
            status = "success"
        except Exception as e:
            message = f"スキル登録中に予期せぬエラーが発生しました: {str(e)}"
            status = "failed"
    else:
        details_str = "\n".join(failed_steps_details)
        message = f"スキル登録に失敗しました。以下の検証ステップで問題が見つかりました:\n{details_str}"
        status = "failed"

    # 最終結果を tool_context.state に保存
    tool_context.state["status"] = status
    tool_context.state["message"] = message
    tool_context.state["registered"] = registered

    return message