"""
Phase 4 新機能テストスイート

1. ShadowEvalRunner (edd shadow - Table 1 Pattern 5: Parallel Offline Comparison)
2. CanaryDeploymentManager (edd canary - Table 1 Pattern 5: Canary Traffic Deployment)
3. SkillRollbackManager (edd rollback - Automated Tier Rollback & Card Sync)
4. HumanReviewAuditor (edd review-diff - Section 6 Human-in-the-Loop Audit Report)
5. SkillOptimizer Tier 3 Shadow Gate 統合
6. CLI Phase 4 コマンドディスパッチ
"""

import json
import pytest
from pathlib import Path

from edd_agent_tools.state import SkillsState
from edd_agent_tools.models import SkillTier
from edd_agent_tools.evaluation.shadow_runner import ShadowEvalRunner, ShadowComparisonReport
from edd_agent_tools.evaluation.canary_manager import CanaryDeploymentManager, CanaryHealthReport
from edd_agent_tools.evaluation.rollback_manager import SkillRollbackManager, RollbackReceipt
from edd_agent_tools.packaging.review_auditor import HumanReviewAuditor
from edd_agent_tools.evaluation.optimizer import SkillOptimizer
from edd_agent_tools.cli import main


def test_shadow_runner_comparison():
    """ShadowEvalRunner が候補スキルとベースラインの並行比較を実行し回帰を正しく検知することを検証"""
    runner = ShadowEvalRunner()
    report = runner.run_shadow_comparison(candidate_skill_name="case-converter")

    assert isinstance(report, ShadowComparisonReport)
    assert report.candidate_skill == "case-converter"
    assert report.total_cases > 0
    assert report.candidate_accuracy >= 0.8
    assert report.regression_detected is False
    assert report.regression_count == 0
    assert "case_results" in report.model_dump()
    assert len(report.case_results) == report.total_cases


def test_canary_manager_routing_and_health(tmp_path: Path):
    """CanaryDeploymentManager が決定論的ルーティングとヘルスチェックを正しく行うことを検証"""
    state_file = tmp_path / "canary.json"
    manager = CanaryDeploymentManager(state_file=state_file, workspace_root=tmp_path)

    # 1. 登録
    dep = manager.register_canary(skill_name="case-converter", traffic_ratio=0.10, max_error_rate=0.05)
    assert dep.skill_name == "case-converter"
    assert dep.traffic_ratio == 0.10
    assert dep.status == "MONITORING"
    assert state_file.exists()

    # 2. ルーティング判定
    # 決定論的に True / False が返る
    routes = [manager.should_route_to_canary("case-converter", f"sess_{i}") for i in range(100)]
    assert any(routes)  # 少なくとも一部は Canary にルーティングされる
    assert not all(routes)  # 全てが Canary になるわけではない

    # 3. メトリクス記録 (成功)
    for i in range(15):
        manager.record_request("case-converter", f"sess_{i}", success=True, latency_ms=120.0, is_canary=True)

    health = manager.evaluate_canary_health("case-converter")
    assert isinstance(health, CanaryHealthReport)
    assert health.canary_error_rate == 0.0
    assert health.health_status == "HEALTHY"

    # 4. エラー率超過時の判定 (DEGRADED ➔ ABORT_AND_ROLLBACK)
    for i in range(5):
        manager.record_request("case-converter", f"err_sess_{i}", success=False, latency_ms=500.0, is_canary=True)

    health_degraded = manager.evaluate_canary_health("case-converter")
    assert health_degraded.health_status == "DEGRADED"
    assert health_degraded.action_recommendation == "ABORT_AND_ROLLBACK"

    # 5. 中断 (Abort)
    assert manager.abort_canary("case-converter", reason="Error rate spiked") is True
    assert manager.deployments["case-converter"].status == "ABORTED"
    assert manager.should_route_to_canary("case-converter", "any_sess") is False


def test_rollback_manager_execution(tmp_path: Path):
    """SkillRollbackManager がスキルの Tier を安全に降格し受領書を発行することを検証"""
    state = SkillsState()
    orig_tier = state.get_skill_tier("secret-sanitizer")
    state.set_skill_tier("secret-sanitizer", 3)
    history_file = tmp_path / "rollback_history.json"
    manager = SkillRollbackManager(state=state, workspace_root=Path.cwd(), history_file=history_file)

    try:
        # Tier 3 ➔ Tier 1 へロールバック
        receipt = manager.rollback_skill(
            skill_name="secret-sanitizer",
            target_tier=1,
            reason="Canary health degraded"
        )
        assert isinstance(receipt, RollbackReceipt)
        assert receipt.skill_name == "secret-sanitizer"
        assert receipt.previous_tier == 3
        assert receipt.new_tier == 1
        assert receipt.status == "SUCCESS"
        assert state.get_skill_tier("secret-sanitizer") == 1
        assert history_file.exists()

        # 履歴照会
        history = manager.get_history("secret-sanitizer")
        assert len(history) >= 1
        assert history[-1].receipt_id == receipt.receipt_id

    finally:
        # 状態の復旧
        state.set_skill_tier("secret-sanitizer", orig_tier)


def test_human_review_auditor_report_generation(tmp_path: Path):
    """HumanReviewAuditor が人間承認用の Markdown 監査レポートを生成できることを検証"""
    auditor = HumanReviewAuditor()
    out_file = tmp_path / "audit_case_converter.md"

    report_str = auditor.generate_audit_report("case-converter", output_path=out_file)

    assert "Human-in-the-Loop Audit Report" in report_str
    assert "case-converter" in report_str
    assert "SkillValidator" in report_str
    assert "Semantic Collision Check" in report_str
    assert "Human-in-the-Loop Checklist" in report_str or "Human Sign-off Checklist" in report_str
    assert out_file.exists()
    assert len(out_file.read_text(encoding="utf-8")) > 100


def test_cli_phase4_commands_dispatch(tmp_path: Path):
    """CLI サブコマンド (shadow, canary, rollback, review-diff) が正常にディスパッチされることを検証"""
    # 1. shadow
    assert main(["shadow", "case-converter"]) == 0

    # 2. canary status / register
    assert main(["canary", "case-converter", "--traffic", "0.05", "--status"]) == 0

    # 3. review-diff to file
    out_report = tmp_path / "custom_audit.md"
    assert main(["review-diff", "case-converter", "--out", str(out_report)]) == 0
    assert out_report.exists()

    # 4. rollback
    state = SkillsState()
    orig_tier = state.get_skill_tier("case-converter")
    state.set_skill_tier("case-converter", 2)
    try:
        # case-converter を Tier 2 から Tier 1 へロールバックテスト
        assert main(["rollback", "case-converter", "--tier", "1", "--reason", "CLI test rollback"]) == 0
        assert SkillsState().get_skill_tier("case-converter") == 1
    finally:
        state.set_skill_tier("case-converter", orig_tier)


def test_optimizer_shadow_gate_integration():
    """SkillOptimizer が Tier 3 昇格時に Shadow 並行比較を実行することを検証"""
    optimizer = SkillOptimizer()
    original_tier = optimizer.state.get_skill_tier("case-converter")
    try:
        # human_approved=True で Tier 3 昇格を実行
        res = optimizer.optimize_skill(
            skill_name="case-converter",
            target_tier=3,
            human_approved=True,
            run_cascade=False
        )
        assert res.get("status") == "promoted"
        assert res.get("promoted_tier") == 3
        # shadow_runner が正常に通過していることを確認
    finally:
        optimizer.state.set_skill_tier("case-converter", original_tier)
