import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools import SkillRegistry, EvalRunResult

from .models import Input

def process_message(params: Input, tool_context: ToolContext) -> str:
    """
    ADK eval テストを実行し、結果を ToolContext.state に格納します。
    """
    skill = params.skill
    eval_set_path = params.eval_set_path
    threshold_accuracy = params.threshold_accuracy if params.threshold_accuracy is not None else 1.0
    timeout_seconds = params.timeout_seconds if params.timeout_seconds is not None else 180

    if not skill:
        raise ValueError("エラー: 'skill' は必須です。")
        
    registry = SkillRegistry()
    target_skill = registry.get_skill(name=skill)

    # eval_set_path が指定されていない場合は自動解決する（test-executorはユニットテストがデフォルト）
    if not eval_set_path:
        eval_set_path = target_skill.get_eval_set_path("unit")

    try:
        # 1. 共通パッケージを用いて設定ファイルパスの取得・自動生成
        config_file_path = target_skill.get_eval(eval_set_path).prepare_config()
            
        print(f"Using eval config file: {config_file_path}")

        print(f"Running test-executor for skill: {skill}")
        print(f"Eval set: {eval_set_path}")
        print(f"Threshold accuracy: {threshold_accuracy:.4f}, Timeout: {timeout_seconds}s")

        # 環境変数の設定
        env = {
            "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
            "SKILL": skill
        }

        # 2. adk eval の実行 (SkillEval に完全に委譲)
        eval_obj = target_skill.get_eval(eval_set_path)
        result: EvalRunResult = eval_obj.execute(
            timeout_seconds=timeout_seconds,
            env_vars=env,
            config_file_path=config_file_path
        )

        accuracy = result.accuracy
        print(f"解析結果: 合格 = {result.passed}, 不合格 = {result.failed}, 合計 = {result.total}, 精度 = {accuracy:.4f}")

        # 3. 合否判定
        status = "passed" if accuracy >= threshold_accuracy else "failed"
        message = f"Accuracy {accuracy:.4f} is {'greater than or equal to' if status == 'passed' else 'less than'} threshold {threshold_accuracy:.4f}."
        if status == "failed" and result.detail_file_path:
            message += f"\n詳細な不合格理由は、以下の結果ファイルを参照してください：\n{result.detail_file_path}"
        
        # 4. 結果を ToolContext.state に格納
        tool_context.state.update({
            "status": status,
            "message": message,
            "accuracy": accuracy,
            "threshold_accuracy": threshold_accuracy
        })

        if status == "passed":
            print(f"\n🎉 テスト合格! 精度 {accuracy:.4f} >= 閾値 {threshold_accuracy:.4f}")
            return message
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