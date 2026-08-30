import os
import json
import glob
from pathlib import Path
from typing import Optional, Any
from edd_agent_tools.evaluation.models import EvalDetailReport


class SkillTests:
    """スキルの tests/ ディレクトリ配下のテスト仕様データ（evalsets, fixtures）および
    実行結果ログ（results）を型安全に管理・アクセスするためのドメインクラス。
    """

    def __init__(self, skill_root_dir: str):
        self.skill_root_dir = os.path.abspath(skill_root_dir)
        self.tests_dir = os.path.join(self.skill_root_dir, "tests")
        self.results_dir = os.path.join(self.tests_dir, "results")
        self.fixtures_dir = os.path.join(self.tests_dir, "fixtures")

    @property
    def latest_report_path(self) -> str:
        """最新のテスト実行詳細レポート（JSON）の絶対パス。"""
        return os.path.join(self.results_dir, "latest_report.json")

    def get_evalset_path(self, test_type: str) -> Optional[str]:
        """指定されたテスト種別（trigger, contract, unit, golden, judge, adversarial 等）に対応する
        テストケース定義ファイル（*.evalset.json）のパスを探索・解決します。

        Args:
            test_type: テストの種別文字列。

        Returns:
            発見された *.evalset.json の絶対パス。存在しない場合は None。
        """
        if not os.path.exists(self.tests_dir):
            return None

        raw_name = os.path.basename(self.skill_root_dir)
        name_under = raw_name.replace('-', '_')
        name_hyphen = raw_name.replace('_', '-')

        candidates = []
        for name in {raw_name, name_under, name_hyphen}:
            candidates.extend([
                f"{name}_{test_type}.evalset.json",
                f"{name}-{test_type}.evalset.json",
                f"{name}_{test_type}_eval.evalset.json",
                f"{name}-{test_type}_eval.evalset.json",
            ])
            if test_type == "contract":
                candidates.extend([
                    f"{name}_unit.evalset.json",
                    f"{name}-unit.evalset.json",
                    f"{name}_unit_eval.evalset.json",
                ])
            elif test_type == "unit":
                candidates.extend([
                    f"{name}_contract.evalset.json",
                    f"{name}-contract.evalset.json",
                ])

        candidates.extend([
            f"{test_type}.evalset.json",
            f"{test_type}_eval.evalset.json",
        ])
        if test_type == "contract":
            candidates.append("unit.evalset.json")
        elif test_type == "unit":
            candidates.append("contract.evalset.json")


        for candidate in candidates:
            candidate_path = os.path.join(self.tests_dir, candidate)
            if os.path.isfile(candidate_path):
                return os.path.abspath(candidate_path)

        # 部分一致で evalset.json をフォールバック探索
        pattern = os.path.join(self.tests_dir, f"*{test_type}*.evalset.json")
        matches = glob.glob(pattern)
        if matches:
            return os.path.abspath(matches[0])

        return None

    def save_report(
        self,
        report: EvalDetailReport | dict[str, Any],
        test_type: Optional[str] = None
    ) -> str:
        """テスト実行レポートを results/ 配下に保存し、latest_report.json も同時に更新します。

        Args:
            report: 保存する EvalDetailReport インスタンスまたは辞書データ。
            test_type: テスト種別（省略時は report 内の test_type を使用）。

        Returns:
            保存された latest_report.json の絶対パス。
        """
        os.makedirs(self.results_dir, exist_ok=True)

        if isinstance(report, dict):
            report_obj = EvalDetailReport.model_validate(report)
        else:
            report_obj = report

        resolved_test_type = test_type or report_obj.test_type
        json_data = report_obj.model_dump_json(indent=2)

        # 1. テスト種別ごとの結果ファイル保存（例: contract_test_result.json）
        if resolved_test_type:
            type_specific_path = os.path.join(self.results_dir, f"{resolved_test_type}_test_result.json")
            with open(type_specific_path, "w", encoding="utf-8") as f:
                f.write(json_data)

        # 2. latest_report.json の更新
        with open(self.latest_report_path, "w", encoding="utf-8") as f:
            f.write(json_data)

        return self.latest_report_path

    def load_latest_report(self) -> Optional[EvalDetailReport]:
        """最新のテスト実行レポート（latest_report.json）をロードして返します。

        Returns:
            ロードされた EvalDetailReport オブジェクト。ファイルが存在しない場合は None。
        """
        if not os.path.isfile(self.latest_report_path):
            return None

        try:
            with open(self.latest_report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return EvalDetailReport.model_validate(data)
        except Exception as e:
            print(f"[SkillTests] Failed to load latest report from {self.latest_report_path}: {e}")
            return None

    def load_report(self, test_type: str) -> Optional[EvalDetailReport]:
        """指定されたテスト種別の結果レポート（例: contract_test_result.json）をロードして返します。

        Args:
            test_type: テスト種別文字列。

        Returns:
            ロードされた EvalDetailReport オブジェクト。ファイルが存在しない場合は None。
        """
        target_path = os.path.join(self.results_dir, f"{test_type}_test_result.json")
        if not os.path.isfile(target_path):
            return None

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return EvalDetailReport.model_validate(data)
        except Exception as e:
            print(f"[SkillTests] Failed to load report from {target_path}: {e}")
            return None

    def list_reports(self) -> list[str]:
        """results/ 配下に存在する全レポートファイルの絶対パスリストを返します。"""
        if not os.path.exists(self.results_dir):
            return []
        return [
            os.path.abspath(p)
            for p in glob.glob(os.path.join(self.results_dir, "*.json"))
        ]

    def list_evalsets(self) -> list[str]:
        """tests/ 配下に存在する全 *.evalset.json ファイルの絶対パスリストを返します。"""
        if not os.path.exists(self.tests_dir):
            return []
        return [
            os.path.abspath(p)
            for p in glob.glob(os.path.join(self.tests_dir, "*.evalset.json"))
        ]
