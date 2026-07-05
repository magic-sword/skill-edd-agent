import os
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

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


class UnitEval(SkillEval):
    @property
    def eval_type(self) -> str:
        return "unit"

    def get_default_config(self) -> dict:
        return {"criteria": {"response_match_score": 0.8}}


class TriggerEval(SkillEval):
    @property
    def eval_type(self) -> str:
        return "trigger"

    def get_default_config(self) -> dict:
        return {"criteria": {"response_match_score": 0.8}}
