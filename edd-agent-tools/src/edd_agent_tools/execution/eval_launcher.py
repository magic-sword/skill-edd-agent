import argparse
import asyncio
import json
import os
import sys

try:
    from google.adk.evaluation.agent_evaluator import AgentEvaluator
    from google.adk.evaluation.eval_config import get_eval_metrics_from_config, get_evaluation_criteria_or_default
    from google.adk.evaluation.in_memory_eval_sets_manager import InMemoryEvalSetsManager
    from google.adk.evaluation.local_eval_sets_manager import load_eval_set_from_file
    from google.adk.evaluation.local_eval_service import LocalEvalService
    from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager
    from google.adk.evaluation.simulation.user_simulator_provider import UserSimulatorProvider
    from google.adk.evaluation.evaluator import EvalStatus
    from google.adk.cli.cli_eval import _collect_inferences, _collect_eval_results, get_root_agent
except ImportError as e:
    print(f"Error: ADK evaluation dependencies are not installed: {e}", file=sys.stderr)
    sys.exit(1)

async def main():
    parser = argparse.ArgumentParser(description="ADK Python API Eval Launcher")
    parser.add_argument("agent_dir", help="エージェントモジュールの配置ディレクトリ")
    parser.add_argument("eval_set_path", help="評価セット（.test.json）のファイルパス")
    parser.add_argument("--config_file_path", help="評価定義（test_config.json）のファイルパス")
    args = parser.parse_args()

    agent_dir = os.path.abspath(args.agent_dir)
    eval_set_path = os.path.abspath(args.eval_set_path)
    config_file_path = os.path.abspath(args.config_file_path) if args.config_file_path else None

    # 1. 各種コンフィグのロードとADK評価器の準備
    eval_config = get_evaluation_criteria_or_default(config_file_path)
    eval_metrics = get_eval_metrics_from_config(eval_config)
    
    root_agent = get_root_agent(agent_dir)
    app_name = os.path.basename(agent_dir)
    agents_dir = os.path.dirname(agent_dir)

    eval_sets_manager = InMemoryEvalSetsManager()
    eval_set = load_eval_set_from_file(eval_set_path, eval_set_path)
    
    eval_sets_manager.create_eval_set(app_name=app_name, eval_set_id=eval_set.eval_set_id)
    for eval_case in eval_set.eval_cases:
        eval_sets_manager.add_eval_case(app_name=app_name, eval_set_id=eval_set.eval_set_id, eval_case=eval_case)

    # 2. LocalEvalServiceの構成
    eval_set_results_manager = LocalEvalSetResultsManager(agents_dir=agents_dir)
    user_simulator_provider = UserSimulatorProvider(user_simulator_config=eval_config.user_simulator_config)
    
    from google.adk.evaluation.metric_evaluator_registry import DEFAULT_METRIC_EVALUATOR_REGISTRY
    metric_evaluator_registry = DEFAULT_METRIC_EVALUATOR_REGISTRY

    eval_service = LocalEvalService(
        root_agent=root_agent,
        eval_sets_manager=eval_sets_manager,
        eval_set_results_manager=eval_set_results_manager,
        user_simulator_provider=user_simulator_provider,
        metric_evaluator_registry=metric_evaluator_registry,
    )

    # 3. 評価の実行
    from google.adk.evaluation.base_eval_service import InferenceRequest, InferenceConfig
    inference_requests = [
        InferenceRequest(
            app_name=app_name,
            eval_set_id=eval_set.eval_set_id,
            eval_case_ids=[],
            inference_config=InferenceConfig(),
        )
    ]

    inference_results = await _collect_inferences(inference_requests=inference_requests, eval_service=eval_service)
    eval_results = await _collect_eval_results(
        inference_results=inference_results,
        eval_service=eval_service,
        eval_metrics=eval_metrics,
    )

    # 4. 結果レポートをディスクに保存 & パス特定
    detail_file_path = None
    history_dir = os.path.join(agents_dir, app_name, ".adk/eval_history")
    
    if os.path.exists(history_dir):
        files = [
            os.path.join(history_dir, f)
            for f in os.listdir(history_dir)
            if f.endswith(".evalset_result.json")
        ]
        if files:
            detail_file_path = max(files, key=os.path.getmtime)

    # 5. 合否カウントの集計
    passed = 0
    total = len(eval_results)
    for eval_result in eval_results:
        if eval_result.final_eval_status == EvalStatus.PASSED:
            passed += 1

    accuracy = passed / total if total > 0 else 0.0

    # 6. PydanticモデルをJSON出力
    from edd_agent_tools.models import EvalRunResult
    result_model = EvalRunResult(
        passed=passed,
        failed=total - passed,
        total=total,
        accuracy=accuracy,
        detail_file_path=detail_file_path
    )
    print(result_model.model_dump_json())

if __name__ == "__main__":
    asyncio.run(main())
