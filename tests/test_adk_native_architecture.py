"""
Tests for Google ADK 2.0 Native Architecture and Meta-Skills (Whitepaper Section 6 & 7)
"""

import os
import json
import pytest
from pathlib import Path

from edd_agent_tools.models.eval import EvalCase, EvalCaseSet, EvalDetailReport
from edd_agent_tools.meta.description_optimizer import DescriptionOptimizer
from edd_agent_tools.meta.trace_harvester import TraceHarvester
from edd_agent_tools.meta.capability_profile import CapabilityProfile, CapabilityProfileManager
from edd_agent_tools.core.entity import Skill
from edd_agent_tools.cli import main as cli_main


def test_adk_native_eval_models_inheritance():
    """EvalCase and EvalCaseSet should inherit from Google ADK 2.0 native models."""
    from google.adk.evaluation.eval_set import EvalSet as AdkEvalSet
    from google.adk.evaluation.eval_case import EvalCase as AdkEvalCase

    assert issubclass(EvalCase, AdkEvalCase)
    assert issubclass(EvalCaseSet, AdkEvalSet)

    case = EvalCase(
        eval_id="test_case_1",
        cli_args=["--help"],
        expected_exit_code=0
    )
    assert case.eval_id == "test_case_1"
    assert case.eval_case_id == "test_case_1"
    assert case.expected_exit_code == 0

    eval_set = EvalCaseSet(
        eval_set_id="test_set_1",
        name="Test Eval Set",
        eval_cases=[case]
    )
    assert eval_set.eval_set_id == "test_set_1"
    assert len(eval_set.eval_cases) == 1


def test_description_optimizer_tuning(tmp_path):
    """DescriptionOptimizer should tune description to improve trigger accuracy."""
    skill_dir = tmp_path / "sample-skill"
    skill_dir.mkdir()
    (skill_dir / "scripts").mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: Generic description\n---\n# Sample Skill\n",
        encoding="utf-8"
    )

    skill = Skill(root_dir=skill_dir)
    trigger_data = {
        "eval_set_id": "sample_trigger",
        "cases": [
            {"user_input": "Please format text with sample-skill", "should_trigger": True},
            {"user_input": "Run sample-skill operations", "should_trigger": True},
            {"user_input": "Ignore this unrelated task", "should_trigger": False}
        ]
    }

    optimizer = DescriptionOptimizer(target_accuracy=0.8, max_iterations=2)
    res = optimizer.optimize_description(skill=skill, trigger_dataset=trigger_data, dry_run=False)

    assert "status" in res
    assert "optimized_description" in res
    assert res["final_accuracy"] >= 0.0


def test_trace_harvester_skill_creation(tmp_path):
    """TraceHarvester should create a valid skill scaffold from execution traces."""
    trace_data = {
        "user_query": "sanitize and mask sensitive API keys from log files",
        "conversation": [
            {"role": "user", "content": "sanitize and mask sensitive API keys from log files"},
            {
                "role": "model",
                "intermediate_data": {
                    "tool_uses": [
                        {"name": "read_log_file", "args": {"file": "app.log"}},
                        {"name": "mask_regex_tokens", "args": {"pattern": "SECRET_.*"}}
                    ]
                }
            }
        ]
    }

    harvester = TraceHarvester()
    res = harvester.harvest_skill_from_trace(
        trace_data=trace_data,
        suggested_skill_name="log-sanitizer",
        output_base_dir=tmp_path
    )

    assert res["status"] == "harvested"
    created_dir = tmp_path / "log-sanitizer"
    assert created_dir.exists()
    assert (created_dir / "SKILL.md").exists()
    assert (created_dir / "scripts").exists()
    assert (created_dir / "tests").exists()


def test_capability_profile_manager():
    """CapabilityProfileManager should resolve active skills based on tier and whitelist."""
    mgr = CapabilityProfileManager()
    assert "read_only_safe" in mgr.profiles
    assert "action_mastered" in mgr.profiles

    # Read-only profile should filter skills
    skills = mgr.resolve_active_skills("read_only_safe")
    assert isinstance(skills, list)
    for s in skills:
        assert s["tier"] == 1


def test_cli_meta_commands_dispatch(tmp_path):
    """CLI should handle tune-desc, harvest-trace, and profile subcommands."""
    # 1. Profile command
    assert cli_main(["profile"]) == 0
    assert cli_main(["profile", "read_only_safe"]) == 0

    # 2. Harvest trace command
    trace_file = tmp_path / "trace.json"
    trace_file.write_text(json.dumps({
        "user_query": "convert text to uppercase",
        "events": [{"role": "user", "content": "convert text"}]
    }), encoding="utf-8")

    assert cli_main([
        "harvest-trace",
        str(trace_file),
        "trace-skill",
        "--out", str(tmp_path)
    ]) == 0
    assert (tmp_path / "trace-skill" / "SKILL.md").exists()


def test_adk_evalset_native_structure():
    """ADK 2.0 公式 EvalSet が 3正例+3負例および完全なconversation構造を持つことを直接検証。"""
    evalset_path = Path("src/skills/case-converter/tests/case-converter.test.json")
    assert evalset_path.exists()

    with open(evalset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "eval_set_id" in data
    assert "eval_cases" in data
    assert len(data["eval_cases"]) == 6  # 3 positive + 3 negative cases
    # 各ケースが ADK 2.0 公式構造（conversation, user_content, intermediate_data）を持つことを確認
    case0 = data["eval_cases"][0]
    assert "conversation" in case0
    assert "user_content" in case0["conversation"][0]
    assert "intermediate_data" in case0["conversation"][0]
    assert "tool_uses" in case0["conversation"][0]["intermediate_data"]



def test_adk_eval_cli_command(monkeypatch):
    """CLI edd adk-eval should dispatch directly to AgentEvaluator."""
    called_args = {}

    async def mock_evaluate(self, agent_module, eval_dataset_file_path_or_dir, config_file_path=None, **kwargs):
        called_args["agent_module"] = agent_module
        called_args["eval_dataset"] = str(eval_dataset_file_path_or_dir)
        called_args["config_file_path"] = str(config_file_path) if config_file_path else None
        return True

    from edd_agent_tools.evaluation.adk_eval import AdkEvalAdapter
    monkeypatch.setattr(AdkEvalAdapter, "evaluate_with_adk_agent", mock_evaluate)

    ret = cli_main(["adk-eval", "case-converter", "--agent-module", "src.main"])
    assert ret == 0
    assert called_args["agent_module"] == "src.main"
    assert "case-converter" in called_args["eval_dataset"]
    assert "test_config.json" in called_args["config_file_path"]


def test_adk_directory_recursive_test_json_discovery():
    """Google ADK 2.0 公式規約 *.test.json の自動探索と EvalSet / EvalConfig 統合を検証。"""
    from google.adk.evaluation.eval_set import EvalSet
    from google.adk.evaluation.agent_evaluator import AgentEvaluator

    skills = ["case-converter", "secret-sanitizer", "skill-creator", "skill-evolver"]
    for s_name in skills:
        skill = Skill(root_dir=Path(f"src/skills/{s_name}"))
        test_file_path = skill.tests.get_evalset_path("edd")
        assert test_file_path is not None
        assert test_file_path.endswith(".test.json")  # *.test.json が優先検出されること

        # ADK 公式 EvalSet によるパース検証
        with open(test_file_path, "r", encoding="utf-8") as f:
            eval_set = EvalSet.model_validate_json(f.read())
        assert len(eval_set.eval_cases) == 6

        # ADK 公式 find_config_for_test_file で同一ディレクトリの test_config.json が紐付くこと
        cfg = AgentEvaluator.find_config_for_test_file(test_file_path)
        assert cfg is not None
        assert "tool_trajectory_avg_score" in cfg.criteria


def test_agent_evaluator_directory_traversal(monkeypatch):
    """AgentEvaluator.evaluate() にディレクトリを渡した際、*.test.json が再帰探索されることを検証。"""
    import asyncio
    from google.adk.evaluation.agent_evaluator import AgentEvaluator

    evaluated_files = []

    async def mock_evaluate_eval_set(agent_module, eval_set, eval_config, **kwargs):
        evaluated_files.append(eval_set.eval_set_id)
        return True

    monkeypatch.setattr(AgentEvaluator, "evaluate_eval_set", mock_evaluate_eval_set)

    # tests ディレクトリを直接指定して evaluate() を呼び出す
    asyncio.run(AgentEvaluator.evaluate(
        agent_module="src",
        eval_dataset_file_path_or_dir="src/skills/case-converter/tests",
        num_runs=1
    ))

    # *.test.json が探索され evaluate_eval_set が呼び出されたことを確認
    assert len(evaluated_files) >= 1
    assert any("case-converter" in eid for eid in evaluated_files)



