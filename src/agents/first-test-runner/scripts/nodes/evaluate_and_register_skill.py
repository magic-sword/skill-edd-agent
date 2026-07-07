from google.adk.tools import ToolContext

def run_evaluate_and_register_skill_step(tool_context: ToolContext) -> str:
    # 先行ノードから検証結果とスキル名を取得
    # validation_results は、各検証ステップの結果を表す辞書のリストを想定
    # 例: [{"step_name": "Schema Validation", "status": "success"}, {"step_name": "API Test", "status": "failure", "details": "Endpoint not reachable"}]
    validation_results = tool_context.state.get("validation_results", [])
    skill_name = tool_context.state.get("skill_name", "Unknown Skill")

    failed_validations = []
    all_successful = True

    for result in validation_results:
        if result.get("status") == "failure":
            all_successful = False
            failed_validations.append(result)

    if all_successful:
        # すべての検証が成功した場合、スキルをTier 1として登録
        registration_status = {
            "skill_name": skill_name,
            "tier": "Tier 1",
            "status": "registered",
            "message": f"Skill '{skill_name}' successfully registered as Tier 1."
        }
        tool_context.state.set("registration_status", registration_status)
        return_message = f"Skill '{skill_name}' successfully registered as Tier 1."
    else:
        # 失敗した検証がある場合、その詳細を収集
        failure_details = {
            "skill_name": skill_name,
            "status": "registration_failed",
            "reason": "One or more validation steps failed.",
            "failed_steps": failed_validations
        }
        tool_context.state.set("registration_failure_details", failure_details)
        
        # 失敗の詳細を文字列として返す
        failed_step_names = [step.get("step_name", "Unknown Step") for step in failed_validations]
        return_message = f"Skill registration failed for '{skill_name}'. Failed steps: {', '.join(failed_step_names)}. See 'registration_failure_details' for more information."
    
    return return_message