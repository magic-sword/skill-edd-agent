import pytest
from edd_agent_tools.evaluation import (
    TelemetryCollector,
    DiagnosticAnalyzer,
    EDDReportFormatter,
    EDDMetaSkillBridge,
)
from edd_agent_tools.models.telemetry import SessionTelemetry, StepTelemetry


def test_telemetry_collector_and_analyzer():
    collector = TelemetryCollector(game_id="test_env_01", title="TestEnv")
    collector.start_step()
    collector.record_step(
        step_index=0,
        action_id=1,
        action_name="ACTION1",
        state_before="hash1",
        state_after="hash2",
        pixels_changed=5,
        is_effective=True,
    )
    collector.start_step()
    collector.record_step(
        step_index=1,
        action_id=1,
        action_name="ACTION1",
        state_before="hash2",
        state_after="hash2",
        pixels_changed=0,
        is_effective=False,
    )
    session = collector.finish_session(final_state="RUNNING", total_levels_completed=0, total_win_levels=1)

    assert session.total_steps == 2
    assert session.effective_steps == 1
    assert session.effective_ratio == 0.5

    report = DiagnosticAnalyzer.analyze(session)
    assert report.game_id == "test_env_01"
    assert report.total_steps == 2
    assert report.effective_ratio == 0.5
    assert report.dominant_failure_category == "ExplorationTimeout"

    summary_str = EDDReportFormatter.format_console_summary([report])
    assert "test_env_01" in summary_str
    assert "50.0%" in summary_str

    bridge_dict = EDDMetaSkillBridge.to_diagnoser_input(report)
    assert bridge_dict["category"] == "ExplorationTimeout"
    assert "test_env_01" in bridge_dict["root_cause"]


def test_wall_stagnation_detection():
    collector = TelemetryCollector(game_id="wall_env", title="Wall")
    for i in range(10):
        collector.record_step(
            step_index=i,
            action_id=1,
            action_name="ACTION1",
            state_before="h",
            state_after="h",
            pixels_changed=0,
            is_effective=False,
        )
    session = collector.finish_session(final_state="RUNNING")
    report = DiagnosticAnalyzer.analyze(session)
    assert report.dominant_failure_category == "WallStagnationAndActionRejection"
    assert report.max_consecutive_stagnation == 10
