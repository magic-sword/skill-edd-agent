import json
import os
from datetime import datetime
from typing import List
from .schemas import EvalCase, EvalSet, TriggerEvalConfig, TriggerEvalReport

class AssetManager:
    """評価アセットの保存とレポート出力を管理するクラス。"""

    def __init__(self):
        """AssetManager を初期化します。"""
        # パッケージ初期ロード時の循環参照を回避するため、実行時に遅延ローカルインポート
        from edd_agent_tools.skills import SkillsState
        self.skills_state = SkillsState()

    def save_eval_assets(self, skill_name: str, eval_cases: List[EvalCase], target_dir) -> str:
        """生成された評価アセットを保存します。

        Args:
            skill_name: アセット保存対象のスキル名。
            eval_cases: 保存する評価ケースモデルのリスト。
            target_dir: 対象スキルのSkillオブジェクト。

        Returns:
            str: 保存された評価セットファイルのパス。
        """
        # 評価セット全体のモデル化
        eval_set = EvalSet(
            eval_set_id=f"{skill_name}_trigger_eval_set",
            name=f"{skill_name} Trigger Evaluation Set",
            eval_cases=eval_cases
        )

        # 評価設定のモデル化
        config = TriggerEvalConfig()

        eval_obj = target_dir.get_eval("trigger")
        eval_set_filepath = eval_obj.save_eval_set(eval_set.model_dump())
        config_filepath = eval_obj.save_config(config.model_dump())

        print(f"  - テストケースを '{eval_set_filepath}' に保存しました。")
        print(f"  - 評価設定を '{config_filepath}' に保存しました。\n")
        return eval_set_filepath

    def save_report(self, skill_name: str, static_eval_result: dict, generated_cases_file: str, target_dir):
        """詳細レポートを保存します。

        Args:
            skill_name: レポート対象のスキル名。
            static_eval_result: 静的評価の結果。
            generated_cases_file: 生成されたテストケースファイルのパス。
            target_dir: 対象スキルのSkillオブジェクト。
        """
        now_str = datetime.now().isoformat() + "Z"
        report_filepath = os.path.join(target_dir.root_dir, "tests", "trigger_eval_report.json")

        # レポートデータのモデル化
        report = TriggerEvalReport(
            skill=skill_name,
            static_evaluation=static_eval_result,
            generated_cases_file=generated_cases_file,
            status="PASSED" if static_eval_result.get("passed") else "FAILED",
            evaluation_date=now_str
        )

        os.makedirs(os.path.dirname(report_filepath), exist_ok=True)
        with open(report_filepath, 'w', encoding='utf-8') as f:
            json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"  - 詳細レポートを '{report_filepath}' に保存しました。\n")
