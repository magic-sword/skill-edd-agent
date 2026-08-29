from google.adk.tools import ToolContext

def aggregate_test_results(tool_context: ToolContext) -> str:
    """
    先行する全てのテスト結果を集約し、全体の合否を判定します。
    """
    overall_passed = tool_context.state.get("overall_passed", True) # validate_dependenciesで初期化されているはず

    # 各テストの結果を取得し、個別のステータスと全体の合否を更新
    # run_contract_test の結果が 'contract_test_result' などのキーで保存されていると仮定する。
    # merge_result_to_state が 'status' キーで結果をマージする場合、それを参照する。

    # 契約テスト結果
    contract_status_from_state = tool_context.state.get("contract_test_result_status", None) # run_contract_testの結果から取得
    if contract_status_from_state:
        contract_test_passed = (contract_status_from_state == "PASSED")
        tool_context.state.set("contract_test_status", contract_status_from_state)
        overall_passed = overall_passed and contract_test_passed
    else:
        # contract_test_result_status がない場合はテストが実行されていないか失敗とみなす
        tool_context.state.set("contract_test_status", "NOT_RUN")
        overall_passed = False


    # ゴールデンテスト結果
    golden_status_from_state = tool_context.state.get("golden_test_result_status", None)
    if golden_status_from_state:
        golden_test_passed = (golden_status_from_state == "PASSED")
        tool_context.state.set("golden_test_status", golden_status_from_state)
        overall_passed = overall_passed and golden_test_passed
    else:
        tool_context.state.set("golden_test_status", "NOT_RUN")
        overall_passed = False

    # ジャッジテスト結果
    judge_status_from_state = tool_context.state.get("judge_test_result_status", None)
    if judge_status_from_state:
        judge_test_passed = (judge_status_from_state == "PASSED")
        tool_context.state.set("judge_test_status", judge_status_from_state)
        overall_passed = overall_passed and judge_test_passed
    else:
        tool_context.state.set("judge_test_status", "NOT_RUN")
        overall_passed = False

    # 敵対的・限界テスト結果
    adversarial_status_from_state = tool_context.state.get("adversarial_test_result_status", None)
    if adversarial_status_from_state:
        adversarial_test_passed = (adversarial_status_from_state == "PASSED")
        tool_context.state.set("adversarial_test_status", adversarial_status_from_state)
        overall_passed = overall_passed and adversarial_test_passed
    else:
        tool_context.state.set("adversarial_test_status", "NOT_RUN")
        overall_passed = False
    
    # 最終的な全体の合否フラグを更新
    tool_context.state.set("overall_passed", overall_passed)

    if overall_passed:
        result_message = "全てのテストが成功しました。"
        tool_context.state.set("overall_status", "success")
    else:
        result_message = "一部または全てのテストが失敗しました。"
        tool_context.state.set("overall_status", "failed")
        
    return result_message
