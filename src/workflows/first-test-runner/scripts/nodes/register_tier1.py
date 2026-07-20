from google.adk.tools import ToolContext

def run_register_tier1_step(tool_context: ToolContext) -> str:
    """
    すべてのテストに合格したスキルをTier 1としてシステムに登録するカスタム関数。

    Args:
        tool_context: ADKツールコンテキスト。

    Returns:
        処理結果を表現する文字列。
    """
    skill_name = tool_context.state.get("skill_name")
    
    # 依存関係の検証結果を取得
    dependencies_successful = tool_context.state.get("dependencies_validation_successful", False)
    # トリガーテストの結果を取得 (test-executorの出力スキーマに依存)
    trigger_test_successful = tool_context.state.get("trigger_test_is_success", False)
    # 契約テストの結果を取得 (test-executorの出力スキーマに依存)
    contract_test_successful = tool_context.state.get("contract_test_is_success", False)

    # すべての検証とテストが成功したかを判断
    all_tests_passed = dependencies_successful and trigger_test_successful and contract_test_successful

    print("DEBUG tool_context.state contents:")
    try:
        state_dict = tool_context.state.to_dict() if hasattr(tool_context.state, "to_dict") else dict(tool_context.state)
        for k, v in state_dict.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"  Failed to dump state: {e}")
    print(f"DEBUG dependencies_successful={dependencies_successful}, trigger_test_successful={trigger_test_successful}, contract_test_successful={contract_test_successful}")

    onboarding_status = "failed"
    message = ""

    if skill_name is None:
        message = "Error: Skill name not provided in tool_context.state. Cannot register Tier 1 skill."
    elif not all_tests_passed:
        # いずれかのテストが失敗した場合
        message_parts = []
        if not dependencies_successful:
            message_parts.append("Dependency validation failed.")
        if not trigger_test_successful:
            message_parts.append("Trigger test failed.")
        if not contract_test_successful:
            message_parts.append("Contract test failed.")
        message = f"Skill '{skill_name}' failed to register as Tier 1 because: {', '.join(message_parts)}"
    else:
        try:
            from edd_agent_tools.skills import SkillsState, SkillTier
            state = SkillsState()
            skill_obj = state.get_skill(skill_name)
            if not skill_obj:
                raise ValueError(f"Skill '{skill_name}' not found in SkillsState.")
                
            skill_obj.set_tier(SkillTier.READ_ONLY)
            state.register_skill(skill_obj)
            
            onboarding_status = "success"
            message = f"Skill '{skill_name}' successfully registered as Tier 1."
            
            # 登録されたスキル名とステータスを後続ノードのために状態に格納
            tool_context.state["registered_skill_name"] = skill_name

        except Exception as e:
            # 登録処理中にエラーが発生した場合
            onboarding_status = "failed" # Errorもfailedとして扱う
            message = f"Error registering skill '{skill_name}' as Tier 1: {str(e)}"
    
    # design.json の response_parameters に合わせて最終的なステータスとメッセージを設定
    tool_context.state["onboarding_status"] = onboarding_status
    tool_context.state["message"] = message

    return message
