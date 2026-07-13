import os
import asyncio
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from .models import EvalRunResult

class SimulationEvalRunner:
    """
    Gymnasium環境とADKエージェントを接続し、シミュレーション評価を実行するランナー。
    """
    def run_simulation_sync(
        self, 
        env: Any, 
        agent_tool: Any, 
        max_steps: int = 15,
        initial_prompt: str = ""
    ) -> EvalRunResult:
        """シミュレーションを同期的に実行します。"""
        coro = self.run_simulation(
            env=env,
            agent_tool=agent_tool,
            max_steps=max_steps,
            initial_prompt=initial_prompt
        )
        return self._run_coroutine_safe(coro)

    async def run_simulation(
        self, 
        env: Any, 
        agent_tool: Any,  # google.adk.tools.FunctionTool または google.adk.Agent インスタンス
        max_steps: int = 15,
        initial_prompt: str = ""
    ) -> EvalRunResult:
        """
        指定された Gymnasium 環境と ADK エージェントを接続してシミュレーションを実行します。

        Args:
            env: gymnasium.Env を継承したシミュレーション環境インスタンス。
            agent_tool: google.adk.tools.FunctionTool または google.adk.Agent インスタンス。
            max_steps: 最大シミュレーションステップ数。
            initial_prompt: エージェントに最初に与えるタスク指示プロンプト。

        Returns:
            評価結果 (EvalRunResult)
        """
        # 軌跡（ステップごとのログ）を記録するリスト
        trajectory = []
        step_count = 0
        
        # 1. 環境を初期化
        obs, info = env.reset()
        trajectory.append({
            "step": 0,
            "observation": obs,
            "info": info,
            "action": None,
            "reward": 0.0,
            "done": False
        })
        
        print(f"Simulation started. Initial obs: {obs}")
        
        # ループ終了フラグと状態管理
        done = False
        total_reward = 0.0
        
        # 2. 環境の step アクションを ADK のツールとして定義してエージェントにバインド
        # エージェント（LLM）はこのツールを呼び出すことで環境と対話する
        from google.adk.tools import FunctionTool
        
        def execute_env_action(action: str, path: str = "", content: str = "") -> str:
            """環境に対してアクションを実行し、新しい観測結果を返します。

            Args:
                action: 実行するアクション名 (例: write_file, run_pytest, view_file)。
                path: アクション対象のファイルパス（書き込みや表示時に必要）。
                content: ファイルに書き込むコンテンツ内容。

            Returns:
                アクション実行後の新しい環境状態（観測値）。
            """
            nonlocal obs, done, total_reward, step_count
            
            # Pydantic アクションインスタンスへ変換
            from edd_agent_tools.evaluation.models import WriteFileAction, ViewFileAction, RunPytestAction
            
            if action == "write_file":
                action_obj = WriteFileAction(path=path, content=content)
            elif action == "view_file":
                action_obj = ViewFileAction(path=path)
            elif action == "run_pytest":
                action_obj = RunPytestAction()
            else:
                raise ValueError(f"Unknown action: {action}")
                
            obs, reward, terminated, truncated, info = env.step(action_obj)
            done = terminated or truncated
            total_reward += reward
            
            trajectory.append({
                "step": step_count,
                "observation": obs,
                "info": info,
                "action": action_obj.model_dump(),
                "reward": reward,
                "done": done
            })
            
            print(f"[Env Action Log] Executed: {action_obj.model_dump()}")
            print(f"[Env Action Log] Reward: {reward}, Terminated: {terminated}, Truncated: {truncated}")
            print(f"[Env Action Log] New Obs: {obs}")
            
            return f"Action executed successfully. Current environment status: {obs}"

        # FunctionTool でラップする
        execute_env_action_tool = FunctionTool(func=execute_env_action)

        # テスト対象ツールと環境アクションツールを持たせたエージェントを動的に構築
        from google.adk import Agent
        if isinstance(agent_tool, Agent):
            agent = agent_tool
            # すでに登録されている場合は二重登録を防ぐ
            if not any(t.name == "execute_env_action" for t in agent.tools):
                agent.tools.append(execute_env_action_tool)
        else:
            agent = Agent(
                name=f"sim_{agent_tool.name}",
                tools=[agent_tool, execute_env_action_tool]
            )
        
        # 3. ADK Runner の初期化
        from google.adk import Runner
        from google.adk.sessions import InMemorySessionService
        
        session_service = InMemorySessionService()
        adk_runner = Runner(agent=agent, session_service=session_service, app_name="eval_sim")
        
        # エージェントに最初のプロンプトを提示して開始
        current_prompt = (
            f"{initial_prompt}\n\n"
            f"現在の環境状態: {obs}\n"
            f"目標を達成するために `execute_env_action` ツールを呼び出してアクションを実行してください。"
        )
        
        try:
            while not done and step_count < max_steps:
                step_count += 1
                print(f"\n--- Simulation Loop Step {step_count} ---")
                
                # ADK エージェントの実行
                events = await adk_runner.run_debug(current_prompt, quiet=True)
                
                # 最終応答テキストを取得
                response_text = ""
                for event in events:
                    if event.is_final_response() and event.content:
                        response_text = "".join(part.text for part in event.content.parts if part.text)
                        break
                
                print(f"Agent Final Response: {response_text}")
                
                # 次のループ用のプロンプトを更新
                current_prompt = (
                    f"前回の思考・応答: {response_text}\n"
                    f"現在の環境状態: {obs}\n"
                    f"目標が未達成の場合は、引き続き `execute_env_action` を実行してください。"
                )
                
        except Exception as e:
            import traceback
            print(f"Error during simulation loop at step {step_count}: {e}")
            traceback.print_exc()
            trajectory.append({
                "step": step_count,
                "error": str(e),
                "reward": -0.5
            })
            total_reward -= 0.5
            
        # 最終評価結果の集計
        passed = 1 if (done and total_reward > 0) else 0
        total = 1
        accuracy = float(passed)
        
        # 軌跡ログの書き出し
        detail_log_dir = "/workspace/scratch/eval_history"
        os.makedirs(detail_log_dir, exist_ok=True)
        detail_file = os.path.join(detail_log_dir, f"sim_{agent.name}_{step_count}.json")
        with open(detail_file, "w", encoding="utf-8") as f:
            import json
            json.dump(trajectory, f, indent=2, ensure_ascii=False)

        return EvalRunResult(
            passed=passed,
            failed=total - passed,
            total=total,
            accuracy=accuracy,
            detail_file_path=detail_file
        )

    def _run_coroutine_safe(self, coro):
        """既にイベントループが動いている場合でも、コルーチンを安全に同期実行します。"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(asyncio.run, coro).result()
        else:
            return asyncio.run(coro)
