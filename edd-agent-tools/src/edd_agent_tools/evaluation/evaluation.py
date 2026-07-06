import os
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from edd_agent_tools.models import ModuleType, EvalRunResult

if TYPE_CHECKING:
    from edd_agent_tools.skill import Skill


class SkillEval(ABC):
    """
    スキルの評価（テスト）を管理する基底クラス。
    """
    def __init__(self, skill: "Skill"):
        self.skill = skill

    @property
    def tests_dir(self) -> str:
        """tests ディレクトリの絶対パス"""
        return os.path.join(self.skill.root_dir, "tests")

    def get_test_filepath(self, filename: str) -> str:
        """
        tests ディレクトリ配下のテスト用ファイルの絶対パスを取得し、
        tests ディレクトリが存在しない場合は自動で作成します。
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

    @property
    @abstractmethod
    def use_mock(self) -> bool:
        """評価実行時にモックを使用するかどうかを子クラスが決定します。"""
        pass

    def execute(self, timeout_seconds: int = 180, env_vars: dict = None, config_file_path: str = None) -> EvalRunResult:
        """
        評価を実行し、その結果を返します。
        エージェントの準備、パス解決、評価器の呼び出しのすべてがインプロセスで完結します。
        """
        # 1. 評価設定ファイルの準備
        config_path = config_file_path if config_file_path else self.prepare_config()

        # 2. 自身が決定したポリシー（use_mock）に基づいてディレクトリを用意
        agent_dir = self._prepare_eval_agent_dir(mock=self.use_mock)

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

    def _prepare_eval_agent_dir(self, mock: bool) -> str:
        """adk eval 用の動的エージェントディレクトリを構築し、そのパスを返します。"""
        eval_run_dir = os.path.join("/workspace/scratch", f"eval_run_{self.skill.name.replace('-', '_')}")
        os.makedirs(eval_run_dir, exist_ok=True)
        
        agent_py_content = self._generate_eval_agent_code(mock)
        
        with open(os.path.join(eval_run_dir, "agent.py"), "w", encoding="utf-8") as f:
            f.write(agent_py_content)
            
        with open(os.path.join(eval_run_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("")
            
        return eval_run_dir

    def _generate_eval_agent_code(self, mock: bool) -> str:
        """モジュールタイプ (SKILL または WORKFLOW) に応じて、適切な agent.py コードを生成します。"""
        skill_name = self.skill.name
        skill_root = self.skill.root_dir
        
        # テンプレートファイルのベースディレクトリ解決
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        
        # モックセットアップコードの読み込み
        mock_setup_code = ""
        if mock:
            mock_setup_path = os.path.join(templates_dir, "eval_mock_setup.py.tmpl")
            with open(mock_setup_path, "r", encoding="utf-8") as f:
                mock_setup_code = f.read()
                
        # モジュールタイプ別のテンプレートロードと置換
        if self.skill.metadata.module_type == ModuleType.WORKFLOW:
            tmpl_path = os.path.join(templates_dir, "eval_agent_workflow.py.tmpl")
            with open(tmpl_path, "r", encoding="utf-8") as f:
                template = f.read()
            return template.format(
                skill_root=skill_root,
                skill_name=skill_name,
                mock_setup_code=mock_setup_code
            )
        else:
            tmpl_path = os.path.join(templates_dir, "eval_agent_skill.py.tmpl")
            with open(tmpl_path, "r", encoding="utf-8") as f:
                template = f.read()
            return template.format(
                skill_name=skill_name,
                mock_setup_code=mock_setup_code
            )


class UnitEval(SkillEval):
    @property
    def eval_type(self) -> str:
        return "unit"

    @property
    def use_mock(self) -> bool:
        # ユニットテストはモックを使用しない（通常実行）
        return False

    def get_default_config(self) -> dict:
        return {"criteria": {"response_match_score": 0.8}}


class TriggerEval(SkillEval):
    @property
    def eval_type(self) -> str:
        return "trigger"

    @property
    def use_mock(self) -> bool:
        # トリガーテストはモックを使用する（呼び出し判断のみ）
        return True

    def get_default_config(self) -> dict:
        return {"criteria": {"response_match_score": 0.8}}
