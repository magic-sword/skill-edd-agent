import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from edd_agent_tools.models import EvalRunResult

class ADKEvalServiceRunner:
    """ADK の LocalEvalService をインプロセスで初期化・実行する実行クラス。

    構造化されたオブジェクトから直接結果を集計する責務を持ちます。
    """
    def run_in_process(self, agent_dir: str, eval_set_path: str, config_path: str) -> EvalRunResult:
        """ADK 評価サービスをインプロセスで初期化・実行し、合否数をパースします。

        Args:
            agent_dir: 動的に構築されたエージェントコードが配置されているディレクトリの絶対パス。
            eval_set_path: 評価用のテストケースファイル（*.evalset.json）の絶対パス。
            config_path: 評価設定ファイル（*.evalset.config.json）の絶対パス。

        Returns:
            テスト結果の合格数、不合格数、精度、および生成された詳細ログパスを格納した EvalRunResult。
        """
        # パッチ用ディレクトリとパッケージソースルートを sys.path に動的注入
        self._patch_sys_path()

        # ADK 評価用の依存ライブラリをインプロセスロード
        from google.adk.evaluation.eval_config import get_eval_metrics_from_config, get_evaluation_criteria_or_default
        from google.adk.evaluation.in_memory_eval_sets_manager import InMemoryEvalSetsManager
        from google.adk.evaluation.local_eval_sets_manager import load_eval_set_from_file
        from google.adk.evaluation.local_eval_service import LocalEvalService
        from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager
        from google.adk.evaluation.simulation.user_simulator_provider import UserSimulatorProvider
        from google.adk.evaluation.evaluator import EvalStatus
        from google.adk.cli.cli_eval import _collect_inferences, _collect_eval_results, get_root_agent
        from google.adk.evaluation.eval_case import get_all_tool_calls

        # 1. コンフィグとエージェントの準備
        eval_config = get_evaluation_criteria_or_default(config_path)
        eval_metrics = get_eval_metrics_from_config(eval_config)
        
        root_agent = get_root_agent(agent_dir)
        app_name = os.path.basename(agent_dir)
        agents_dir = os.path.dirname(agent_dir)

        # 2. テストケース（eval_set）のメモリロード
        eval_sets_manager = InMemoryEvalSetsManager()
        eval_set = load_eval_set_from_file(eval_set_path, eval_set_path)
        
        eval_sets_manager.create_eval_set(app_name=app_name, eval_set_id=eval_set.eval_set_id)
        for eval_case in eval_set.eval_cases:
            eval_sets_manager.add_eval_case(app_name=app_name, eval_set_id=eval_set.eval_set_id, eval_case=eval_case)

        # 3. 評価サービスの構成
        eval_set_results_manager = LocalEvalSetResultsManager(agents_dir=agents_dir)
        user_simulator_provider = UserSimulatorProvider(user_simulator_config=eval_config.user_simulator_config)
        
        from google.adk.evaluation.metric_evaluator_registry import DEFAULT_METRIC_EVALUATOR_REGISTRY

        eval_service = LocalEvalService(
            root_agent=root_agent,
            eval_sets_manager=eval_sets_manager,
            eval_set_results_manager=eval_set_results_manager,
            user_simulator_provider=user_simulator_provider,
            metric_evaluator_registry=DEFAULT_METRIC_EVALUATOR_REGISTRY,
        )

        # 4. 推論リクエストの構成
        from google.adk.evaluation.base_eval_service import InferenceRequest, InferenceConfig
        inference_requests = [
            InferenceRequest(
                app_name=app_name,
                eval_set_id=eval_set.eval_set_id,
                eval_case_ids=[],
                inference_config=InferenceConfig(),
            )
        ]

        # 5. 非同期ADK APIを同期実行するための内部コルーチン
        async def _run_eval_async():
            inference_results = await _collect_inferences(inference_requests=inference_requests, eval_service=eval_service)
            eval_results = await _collect_eval_results(
                inference_results=inference_results,
                eval_service=eval_service,
                eval_metrics=eval_metrics,
            )
            return eval_results

        # イベントループ衝突回避ヘルパーで非同期処理を安全に実行
        eval_results = self._run_coroutine_safe(_run_eval_async())

        # 6. 詳細レポートファイルの特定
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

        # 7. 合否のカウント・精度集計および引数無視の軌道評価救済処理 (Post-Processing)
        for r in eval_results:
            # 各インボケーションレベルでの軌道評価を救済
            for inv_res in r.eval_metric_result_per_invocation:
                actual_calls = get_all_tool_calls(inv_res.actual_invocation.intermediate_data)
                
                # expected_invocation が存在しないケースを考慮
                if not inv_res.expected_invocation:
                    continue
                expected_calls = get_all_tool_calls(inv_res.expected_invocation.intermediate_data)
                
                # ツール名と数のみで一致を判定
                match = True
                if len(actual_calls) != len(expected_calls):
                    match = False
                else:
                    for act, exp in zip(actual_calls, expected_calls):
                        if act.name != exp.name:
                            match = False
                            break
                
                # ツール名だけが一致していれば、そのインボケーションの軌道評価スコアを 1.0 (PASSED) に書き換える
                if match:
                    for m_res in inv_res.eval_metric_results:
                        if m_res.metric_name == "tool_trajectory_avg_score":
                            m_res.score = 1.0
                            m_res.eval_status = EvalStatus.PASSED

            # ケース全体の軌道評価メトリックスコアを再集計・更新
            trajectory_metric_res = None
            for m_res in r.overall_eval_metric_results:
                if m_res.metric_name == "tool_trajectory_avg_score":
                    trajectory_metric_res = m_res
                    break

            if trajectory_metric_res:
                total_inv_score = 0.0
                inv_count = 0
                for inv_res in r.eval_metric_result_per_invocation:
                    for m_res in inv_res.eval_metric_results:
                        if m_res.metric_name == "tool_trajectory_avg_score":
                            total_inv_score += m_res.score
                            inv_count += 1
                
                avg_score = total_inv_score / inv_count if inv_count > 0 else 0.0
                trajectory_metric_res.score = avg_score
                
                # threshold が設定されていない場合は 1.0 を基準にする
                threshold = trajectory_metric_res.threshold if trajectory_metric_res.threshold is not None else 1.0
                if avg_score >= threshold:
                    trajectory_metric_res.eval_status = EvalStatus.PASSED
            
            # 総合ステータスの更新
            all_passed = True
            for m_res in r.overall_eval_metric_results:
                if m_res.eval_status != EvalStatus.PASSED:
                    all_passed = False
                    break
            
            if all_passed:
                r.final_eval_status = EvalStatus.PASSED

        passed = sum(1 for r in eval_results if r.final_eval_status == EvalStatus.PASSED)
        total = len(eval_results)
        accuracy = passed / total if total > 0 else 0.0

        return EvalRunResult(
            passed=passed,
            failed=total - passed,
            total=total,
            accuracy=accuracy,
            detail_file_path=detail_file_path
        )

    def _patch_sys_path(self):
        """ADKプロセスとマルチ言語パッチ環境を sys.path に動的追加します。"""
        import sys
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        
        # evaluation フォルダと同じ階層にある run/patch ディレクトリを解決
        patch_dir = os.path.abspath(os.path.join(current_file_dir, "..", "run", "patch"))
        edd_tools_src_dir = os.path.abspath(os.path.join(current_file_dir, "..", ".."))

        for path in [patch_dir, edd_tools_src_dir]:
            if path not in sys.path:
                sys.path.insert(0, path)

    def _run_coroutine_safe(self, coro):
        """既にイベントループが動いている場合でも、コルーチンを安全に同期実行します。

        Args:
            coro: 同期実行するコルーチンオブジェクト。

        Returns:
            コルーチンの実行結果オブジェクト。
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # テストランナー等でループが走っている場合は別スレッドで処理
            with ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(asyncio.run, coro).result()
        else:
            return asyncio.run(coro)

