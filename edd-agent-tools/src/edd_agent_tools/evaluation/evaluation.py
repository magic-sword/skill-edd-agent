import os
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from edd_agent_tools.skills.models import ModuleType
from .models import EvalRunResult

if TYPE_CHECKING:
    from edd_agent_tools.skills import Skill


class SkillEval(ABC):
    """スキルの評価（テスト）を管理する基底クラス。

    Examples:
        >>> from edd_agent_tools.skills import SkillsState
        >>> state = SkillsState()
        >>> skill = state.get_skill("my-sample-skill")

        # 1. 評価用パスまたはタイプ名から SkillEval インスタンスを取得
        >>> eval_obj = skill.get_eval("unit")

        # 2. 評価設定ファイルの準備 (存在しない場合はデフォルト config ファイルを自動生成して保存)
        >>> config_path = eval_obj.prepare_config()

        # 3. テストケースの保存
        >>> eval_set_data = {
        ...     "eval_set_id": "my_sample_eval_set",
        ...     "name": "My Sample Evaluation Set",
        ...     "eval_cases": []
        ... }
        >>> eval_set_path = eval_obj.save_eval_set(eval_set_data)

        # 4. テスト実行 (100% インプロセスで直接実行)
        >>> result = eval_obj.execute()
    """
    def __init__(self, skill: "Skill"):
        self.skill = skill

    @property
    def tests_dir(self) -> str:
        """tests ディレクトリの絶対パス"""
        return os.path.join(self.skill.root_dir, "tests")

    def get_test_filepath(self, filename: str) -> str:
        """tests ディレクトリ配下のテスト用ファイルの絶対パスを取得します。

        tests ディレクトリが存在しない場合は自動で作成します。

        Args:
            filename: 解決するテスト用のファイル名。

        Returns:
            テスト用ファイルの絶対パス。
        """
        tests_dir = self.tests_dir
        os.makedirs(tests_dir, exist_ok=True)
        return os.path.join(tests_dir, filename)

    @property
    @abstractmethod
    def eval_type(self) -> str:
        """評価種別 (unit, trigger など)"""
        pass

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

    @abstractmethod
    def get_default_config(self) -> dict:
        """評価タイプに応じたデフォルト設定を返します。"""
        pass

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



    def execute(self, timeout_seconds: int = 180, env_vars: dict = None, config_file_path: str = None) -> EvalRunResult:
        """評価を実行し、その結果を返します。

        エージェントの準備、パス解決、評価器の呼び出しのすべてがインプロセスで完結します。

        Args:
            timeout_seconds: 評価タイムアウト秒数。デフォルトは 180 秒。
            env_vars: 評価実行時に適用する追加の環境変数。
            config_file_path: 評価設定ファイルのカスタムパス。

        Returns:
            評価結果を集計した EvalRunResult インスタンス。
        """
        # 1. 評価設定ファイルの準備
        config_path = config_file_path if config_file_path else self.prepare_config()

        # 2. 自身が定義するコード生成に基づいてディレクトリを用意
        agent_dir = self._prepare_eval_agent_dir()

        # 3. インプロセス実行器に処理を委譲して実行
        from edd_agent_tools.evaluation.runner import ADKEvalServiceRunner
        runner = ADKEvalServiceRunner()
        
        # 環境変数がある場合は適用
        if env_vars:
            os.environ.update(env_vars)

        return runner.run_in_process(
            agent_dir=agent_dir,
            eval_set_path=self.eval_set_path,
            config_path=config_path
        )

    def _prepare_eval_agent_dir(self) -> str:
        """adk eval 用の動的エージェントディレクトリを構築し、そのパスを返します。

        Returns:
            構築された動的エージェント配置用ディレクトリの絶対パス。
        """
        eval_run_dir = os.path.join("/workspace/scratch", f"eval_run_{self.skill.name.replace('-', '_')}")
        os.makedirs(eval_run_dir, exist_ok=True)

        # ポリモーフィズムにより、具象クラスが実装するエージェントコード生成処理を呼ぶ
        agent_py_content = self.generate_agent_code()

        # agent.py を書き出し
        with open(os.path.join(eval_run_dir, "agent.py"), "w", encoding="utf-8") as f:
            f.write(agent_py_content)

        # テンプレートから __init__.py の内容をロードして書き出し
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        init_tmpl_path = os.path.join(templates_dir, "eval_agent_init.py.tmpl")
        with open(init_tmpl_path, "r", encoding="utf-8") as f:
            init_content = f.read()

        with open(os.path.join(eval_run_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write(init_content)

        return eval_run_dir

    def generate_agent_code(self) -> str:
        """エージェントの実行用 Python コード（agent.py）を生成します（サブクラスで実装）。"""
        raise NotImplementedError

    def _load_base_agent_template(self) -> str:
        """共通のベースエージェントテンプレートコード（Skill または Workflow 用）をロードしてフォーマットします。"""
        skill_name = self.skill.name
        skill_root = self.skill.root_dir
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")

        if self.skill.metadata.module_type == ModuleType.WORKFLOW:
            tmpl_path = os.path.join(templates_dir, "eval_agent_workflow.py.tmpl")
            with open(tmpl_path, "r", encoding="utf-8") as f:
                template = f.read()
            return template.format(
                skill_root=skill_root,
                skill_name=skill_name
            )
        else:
            tmpl_path = os.path.join(templates_dir, "eval_agent_skill.py.tmpl")
            with open(tmpl_path, "r", encoding="utf-8") as f:
                template = f.read()
            return template.format(
                skill_name=skill_name
            )


class UnitEval(SkillEval):
    @property
    def eval_type(self) -> str:
        return "unit"

    def generate_agent_code(self) -> str:
        """ユニットテスト用の通常実行エージェントコードを生成します。"""
        return self._load_base_agent_template()

    def get_default_config(self) -> dict:
        return {"criteria": {"response_match_score": 0.8}}


class TriggerEval(SkillEval):
    @property
    def eval_type(self) -> str:
        return "trigger"

    def generate_agent_code(self) -> str:
        """トリガーテスト用のモック実行エージェントコードを生成します。"""
        base_code = self._load_base_agent_template()

        # モックセットアップ用テンプレートをロードして結合
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        mock_setup_path = os.path.join(templates_dir, "eval_mock_setup.py.tmpl")
        with open(mock_setup_path, "r", encoding="utf-8") as f:
            mock_setup_code = f.read()

        return f"{base_code}\n{mock_setup_code}"

    def get_default_config(self) -> dict:
        return {"criteria": {"response_match_score": 0.8}}


class SimulationEval(SkillEval):
    """シミュレーションベースの動的環境テスト（Gymnasium）を管理する評価クラス。"""
    @property
    def eval_type(self) -> str:
        return "simulation"

    def generate_agent_code(self) -> str:
        """シミュレーション実行用のエージェントコードを生成します。"""
        return self._load_base_agent_template()

    def get_default_config(self) -> dict:
        return {"max_steps": 15, "initial_prompt": "目標に向かって行動してください。"}

    def execute_simulation(self, env: Any, max_steps: int = 15, initial_prompt: str = "") -> EvalRunResult:
        """
        指定された Gymnasium 環境とエージェントを使用してシミュレーションテストを実行します。

        Args:
            env: gymnasium.Env を継承したシミュレーション環境インスタンス。
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
