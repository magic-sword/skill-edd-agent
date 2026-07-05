import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.registry import SkillRegistry

from .output_parser import OutputParser
from .test_runner import TestRunner

def process_message(tool_context: ToolContext):
    """
    ADK eval のモックシミュレーションテストを実行し、結果を ToolContext.state に格納します。
    """
    skill = tool_context.state.get("skill")
    eval_set_path = tool_context.state.get("eval_set_path")
    threshold_accuracy = tool_context.state.get("threshold_accuracy", 1.0)
    timeout_seconds = tool_context.state.get("timeout_seconds", 180)

    if not skill:
        raise ValueError("エラー: 'skill' は必須です。")
        
    registry = SkillRegistry()
    target_skill_dir = registry.get_skill_directory(name=skill)
    test_runner = TestRunner()
    output_parser = OutputParser()

    # eval_set_path が指定されていない場合は自動解決する（mock-executorはトリガーテストがデフォルト）
    if not eval_set_path:
        eval_set_path = target_skill_dir.get_eval_set_path("trigger")

    try:
        # 1. 共通パッケージを用いて設定ファイルパスの取得・自動生成
        config_file_path = target_skill_dir.resolve_eval_config_path(eval_set_path)
        if not os.path.exists(config_file_path):
            test_type = "trigger" if "trigger" in eval_set_path else "unit"
            target_skill_dir.save_eval_config({"criteria": {"response_match_score": 0.8}}, test_type)
            
        print(f"Using eval config file: {config_file_path}")

        # 2. adk eval の実行
        stdout, stderr, return_code = test_runner.run_adk_eval(
            skill=skill,
            eval_set_path=eval_set_path,
            config_file_path=config_file_path,
            timeout_seconds=timeout_seconds
        )

        # 3. 出力結果の解析
        combined_output = stdout + "\n" + stderr
        parsed_results = output_parser.parse_adk_eval_output(combined_output, return_code)
        
        accuracy = parsed_results["accuracy"]
        
        if parsed_results["parsed_from_log"]:
            print(f"解析結果: 合格 = {parsed_results['passed']}, 不合格 = {parsed_results['failed']}, 合計 = {parsed_results['total']}, 精度 = {accuracy:.4f}")
        else:
            print(f"警告: ログからテスト結果数を抽出できませんでした。フォールバック結果を使用します。精度 = {accuracy:.4f}")

        # 4. 合否判定
        status = "passed" if accuracy >= threshold_accuracy else "failed"
        message = f"Accuracy {accuracy:.4f} is {'greater than or equal to' if status == 'passed' else 'less than'} threshold {threshold_accuracy:.4f}."
        
        # 5. 結果を ToolContext.state に格納
        tool_context.state.update({
            "status": status,
            "message": message,
            "accuracy": accuracy,
            "threshold_accuracy": threshold_accuracy
        })

        if status == "passed":
            print(f"\n🎉 テスト合格! 精度 {accuracy:.4f} >= 閾値 {threshold_accuracy:.4f}")
        else:
            print(f"\n❌ テスト不合格! 精度 {accuracy:.4f} < 閾値 {threshold_accuracy:.4f}", file=sys.stderr)
            raise RuntimeError(message)

    except FileNotFoundError as e:
        tool_context.state.update({
            "status": "failed",
            "message": str(e),
            "accuracy": 0.0,
            "threshold_accuracy": threshold_accuracy
        })
        print(f"エラー: {e}", file=sys.stderr)
        raise
    except RuntimeError as e:
        if "status" not in tool_context.state:
             tool_context.state.update({
                "status": "failed",
                "message": str(e),
                "accuracy": 0.0,
                "threshold_accuracy": threshold_accuracy
            })
        print(f"エラー: {e}", file=sys.stderr)
        raise
    except Exception as e:
        tool_context.state.update({
            "status": "failed",
            "message": f"予期せぬエラーが発生しました: {str(e)}",
            "accuracy": 0.0,
            "threshold_accuracy": threshold_accuracy
        })
        print(f"予期せぬエラー: {e}", file=sys.stderr)
        raise

def run_mock_tests(threshold_accuracy: float, tool_context: ToolContext) -> str:
    """
    指定されたスキルのモックシミュレーションテストを実行します。
    """
    skill = tool_context.state.get("skill")
    eval_set_path = tool_context.state.get("trig_eval_set_path")
        
    if not skill:
        raise ValueError("セッション状態に 'skill' が設定されていません。")
        
    registry = SkillRegistry()
    target_skill_dir = registry.get_skill_directory(name=skill)
    
    if not eval_set_path:
        eval_set_path = target_skill_dir.get_eval_set_path("trigger")
        
    # 新規の ToolContext を構築してコンテキストを隔離する
    from google.adk.tools import ToolContext as ADKToolContext
    from edd_agent_tools.testing.mock_context import MockInvocationContext
    
    isolated_context = ADKToolContext(invocation_context=MockInvocationContext())
    isolated_context.state.update({
        "skill": skill,
        "eval_set_path": eval_set_path,
        "threshold_accuracy": threshold_accuracy,
        "timeout_seconds": tool_context.state.get("timeout_seconds", 180)
    })
    
    # 直接 process_message をインプロセスで実行
    process_message(isolated_context)
    
    # 隔離されたコンテキストから直接結果を取得する
    status = isolated_context.state.get("status")
    accuracy = isolated_context.state.get("accuracy", 0.0)
    message = isolated_context.state.get("message", "")
    
    if status != "passed":
        raise RuntimeError(f"モックテストが不合格またはエラーが発生しました: {message}")
        
    return f"Success: Mock tests passed with accuracy >= {threshold_accuracy}."
