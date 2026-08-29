from typing import Optional
from .models import DiagnoseSkillFailureOutput
from .executor import SkillExecutor


def diagnose_skill_failure(
    skill: str,
    report_path: Optional[str] = None,
    test_type: Optional[str] = None
) -> DiagnoseSkillFailureOutput:
    """テスト実行結果レポートとスキルの設計・コードを分析し、失敗の根本原因と構造化改善計画を出力します。

    Args:
        skill: 診断対象となるスキルの論理名。
        report_path: テスト結果レポート（JSON）の絶対パス。省略時は最新の latest_report.json を自動参照します。
        test_type: 特定のテスト種別（例: 'contract', 'trigger' 等）。省略時はレポート内の種別を使用します。

    Returns:
        DiagnoseSkillFailureOutput: 診断結果および策定された改善計画オブジェクト。
    """
    executor = SkillExecutor(
        skill=skill,
        report_path=report_path,
        test_type=test_type
    )
    return executor.execute()
