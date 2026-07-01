#!/usr/bin/env python3
"""
AgentEvaluator API を直接呼び出して評価を実行し、結果を JSON 文字列として標準出力するヘルパースクリプト。
親プロセスとのインポート競合を避けるために別プロセスで実行されます。
"""
import argparse
import json
import os
import sys
import asyncio

# プロジェクトルートをsys.pathに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
sys.path.append(WORKSPACE_ROOT)

import google
import google.auth
import google.auth.transport
google.auth = google.auth
google.auth.transport = google.auth.transport
from google.adk.evaluation.agent_evaluator import AgentEvaluator
from google.adk.evaluation.eval_config import get_eval_metrics_from_config
from google.adk.evaluation.simulation.user_simulator_provider import UserSimulatorProvider
from google.adk.evaluation.eval_set import EvalSet

async def run_eval(eval_set_filepath):
    agent_module = "src.agent"
    
    try:
        # 1. エージェントのロード
        agent = await AgentEvaluator._get_agent_for_eval(
            module_name=agent_module, agent_name=None
        )
        
        # 2. 評価用設定のロード
        eval_config = AgentEvaluator.find_config_for_test_file(eval_set_filepath)
        eval_set = AgentEvaluator._load_eval_set_from_file(
            eval_set_filepath, eval_config, {}
        )
        
        eval_metrics = get_eval_metrics_from_config(eval_config)
        user_simulator_provider = UserSimulatorProvider(
            user_simulator_config=eval_config.user_simulator_config
        )
        
        # 3. 評価の実行 (非公開APIの活用)
        eval_results_by_eval_id = await AgentEvaluator._get_eval_results_by_eval_id(
            agent_for_eval=agent,
            eval_set=eval_set,
            eval_metrics=eval_metrics,
            num_runs=1,
            user_simulator_provider=user_simulator_provider
        )
        
        # 4. 結果の解析
        passed_cases = 0
        total_cases = 0
        details = []
        
        for eval_id, eval_results_per_eval_id in eval_results_by_eval_id.items():
            total_cases += 1
            eval_metric_results = AgentEvaluator._get_eval_metric_results_with_invocation(
                eval_results_per_eval_id
            )
            
            failures_per_eval_case = AgentEvaluator._process_metrics_and_get_failures(
                eval_metric_results=eval_metric_results,
                print_detailed_results=False,
                agent_module=None,
            )
            
            passed = len(failures_per_eval_case) == 0
            if passed:
                passed_cases += 1
                
            details.append({
                "eval_id": eval_id,
                "passed": passed,
                "failures": [str(f) for f in failures_per_eval_case]
            })

        accuracy = passed_cases / total_cases if total_cases > 0 else 0.0
        
        output_data = {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "accuracy": accuracy,
            "details": details
        }
        
        print(json.dumps(output_data))
        
    except Exception as e:
        import traceback
        # エラーが発生した場合は標準エラー出力にスタックトレースを吐く
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval_set", required=True)
    args = parser.parse_args()
    
    asyncio.run(run_eval(args.eval_set))

if __name__ == "__main__":
    main()
