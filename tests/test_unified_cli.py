import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from edd_agent_tools.cli import main as cli_main
from edd_agent_tools.skills.state import SkillsState


def test_unified_cli_list(capfd):
    """edd list が利用可能なスキル一覧を出力することをテストします。"""
    exit_code = cli_main(["list"])
    assert exit_code == 0
    captured = capfd.readouterr()
    assert "Available Agent Skills" in captured.out


def test_unified_cli_init_validate_package(tmp_path, capfd):
    """edd init -> edd validate -> edd package の一連のライフサイクルをテストします。"""
    skill_name = "test-unified-skill"
    parent_dir = tmp_path / "skills"
    parent_dir.mkdir()

    # 1. init
    exit_code = cli_main(["init", skill_name, "--path", str(parent_dir), "--pattern", "workflow"])
    assert exit_code == 0
    skill_dir = parent_dir / skill_name
    assert skill_dir.exists()
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "scripts" / "test_unified_skill.py").exists()

    # 2. validate
    exit_code = cli_main(["validate", str(skill_dir)])
    assert exit_code == 0
    captured = capfd.readouterr()
    assert "Skill is completely valid" in captured.out

    # 3. package
    dist_dir = tmp_path / "dist"
    exit_code = cli_main(["package", str(skill_dir), "--out", str(dist_dir)])
    assert exit_code == 0
    zip_path = dist_dir / f"{skill_name}.zip"
    assert zip_path.exists()


def test_unified_cli_run_dynamic_dispatch(capfd):
    """edd run case-converter および edd case-converter による動的ディスパッチ実行をテストします。"""
    # 1. edd run case-converter --input hello_world --format camel
    exit_code = cli_main(["run", "case-converter", "--input", "hello_world", "--format", "camel"])
    assert exit_code == 0
    captured = capfd.readouterr()
    assert "hello_world" in captured.out or "Processing input" in captured.out

    # 2. edd case-converter (Gitプラグイン方式の動的ディスパッチ)
    exit_code = cli_main(["case-converter", "--input", "foo_bar", "--format", "pascal"])
    assert exit_code == 0
    captured = capfd.readouterr()
    assert "foo_bar" in captured.out or "Processing input" in captured.out


def test_unified_cli_eval_diagnose(capfd):
    """edd eval および edd diagnose の動作をテストします。"""
    # case-converter の評価実行
    exit_code = cli_main(["eval", "case-converter", "--type", "contract"])
    assert exit_code == 0
    captured = capfd.readouterr()
    assert "Evaluation Results for 'case-converter'" in captured.out

    # case-converter の診断出力
    exit_code = cli_main(["diagnose", "case-converter", "--format", "markdown"])
    assert exit_code == 0
    captured = capfd.readouterr()
    assert "Failure Diagnosis for Skill: `case-converter`" in captured.out
