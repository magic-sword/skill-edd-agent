import os
import json
from typing import TYPE_CHECKING, Any
from .models import EvalRunResult

if TYPE_CHECKING:
    from edd_agent_tools.skills import Skill


class SimulationEval:
    """シミュレーションベースの動的環境テスト（Gymnasium）を管理する評価クラス。

    Examples:
        >>> from edd_agent_tools.skills import SkillsState
        >>> state = SkillsState()
        >>> skill = state.get_skill("my-sample-skill")
        >>> eval_obj = SimulationEval(skill)
        
        # 評価設定ファイルの準備
        >>> config_path = eval_obj.prepare_config()
        
        # テストケースの保存
        >>> eval_set_path = eval_obj.save_eval_set({"eval_set_id": "sim_test", "eval_cases": []})
    """
    def __init__(self, skill: "Skill"):
        self.skill = skill

    @property
    def tests_dir(self) -> str:
        """tests ディレクトリの絶対パス"""
        return os.path.join(self.skill.root_dir, "tests")

    def get_test_filepath(self, filename: str) -> str:
        """tests ディレクトリ配下のテスト用ファイルの絶対パスを取得します。"""
        tests_dir = self.tests_dir
        os.makedirs(tests_dir, exist_ok=True)
        return os.path.join(tests_dir, filename)

    @property
    def eval_type(self) -> str:
        """評価種別 (simulation)"""
        return "simulation"

    def _get_filename(self, suffix: str) -> str:
        """一貫した命名規則に従ってテストファイル名を生成します"""
        skill_name_underscore = self.skill.name.replace('-', '_')
        return f"{skill_name_underscore}_{self.eval_type}.{suffix}"

    @property
    def eval_set_path(self) -> str:
        """評価用のテストケースファイル (*.evalset.json) の絶対パスを返します。"""
        filename = self._get_filename("evalset.json")
        return self.get_test_filepath(filename)

    @property
    def config_path(self) -> str:
        """評価用の設定ファイル (*.evalset.config.json) の絶対パスを返します。"""
        filename = self._get_filename("evalset.config.json")
        return self.get_test_filepath(filename)

    def get_default_config(self) -> dict:
        """評価タイプに応じたデフォルト設定を返します。"""
        return {"max_steps": 15, "initial_prompt": "目標に向かって行動してください。"}

    def prepare_config(self) -> str:
        """評価設定ファイルのパスを解決し、存在しない場合はデフォルト設定を生成します。"""
        path = self.config_path
        if not os.path.exists(path):
            self.save_config(self.get_default_config())
        return path

    def save_eval_set(self, data: dict) -> str:
        """テストケースファイルを保存し、保存先パスを返します。"""
        path = self.eval_set_path
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def save_config(self, data: dict) -> str:
        """テスト構成ファイルを保存し、保存先パスを返します。"""
        path = self.config_path
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def execute_simulation(self, env: Any, max_steps: int = 15, initial_prompt: str = "") -> EvalRunResult:
        """
        指定された Gymnasium 環境とエージェントを使用してシミュレーションテストを実行します。

        Args:
            env: WorkspaceEnvProtocol を実装した環境インスタンス。
            max_steps: 最大シミュレーションステップ数。
            initial_prompt: エージェントに最初に与えるタスク指示プロンプト。

        Returns:
            評価結果 (EvalRunResult)
        """
        from edd_agent_tools.evaluation.simulation_runner import SimulationEvalRunner
        
        # 評価対象のスキルツールを取得
        agent_tool = self.skill.get_tool()
        
        runner = SimulationEvalRunner()
        return runner.run_simulation_sync(
            env=env,
            agent_tool=agent_tool,
            max_steps=max_steps,
            initial_prompt=initial_prompt
        )
