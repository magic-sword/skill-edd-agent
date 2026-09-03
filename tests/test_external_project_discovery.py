"""
Tests for dynamic skill discovery in external projects (Zero-Hardcoding).
"""

import os
import json
import pytest
from pathlib import Path

from edd_agent_tools.state import SkillsState
from edd_agent_tools.core.entity import Skill
from edd_agent_tools.adk.toolset import EddSkillToolset
from edd_agent_tools.packaging import SkillScaffolder


def test_external_project_skills_discovery(tmp_path: Path):
    """他プロジェクトのルートにおいて、skills/ 配下に配置されたカスタムスキルが自動検出されることを検証。"""
    # 外部プロジェクトのディレクトリ構造を模擬
    external_root = tmp_path / "my_external_project"
    external_root.mkdir()
    skills_dir = external_root / "skills"
    skills_dir.mkdir()

    # スキルを初期化
    SkillScaffolder.scaffold("custom-pdf-tool", output_base_dir=skills_dir, pattern="workflow")

    # プロジェクトルートを指定して SkillsState を作成
    state = SkillsState(project_root=external_root)
    skills = state.scan_skills()

    assert "custom-pdf-tool" in skills
    skill_obj = state.get_skill("custom-pdf-tool")
    assert skill_obj is not None
    assert skill_obj.name == "custom-pdf-tool"
    assert (Path(skill_obj.root_dir) / "SKILL.md").exists()


def test_adk_toolset_with_external_skills_root(tmp_path: Path):
    """EddSkillToolset が外部ディレクトリを指定された際に、正しくスキル一覧・ロード・実行できることを検証。"""
    custom_root = tmp_path / "custom_agents_skills"
    custom_root.mkdir()

    SkillScaffolder.scaffold("weather-reporter", output_base_dir=custom_root, pattern="task_based")

    toolset = EddSkillToolset(skills_root=custom_root)
    skills = toolset.state.list_skills()

    assert len(skills) >= 1
    assert any(s.name == "weather-reporter" for s in skills)

    # ロードテスト
    from edd_agent_tools.core import SkillPackage
    pkg = SkillPackage(custom_root / "weather-reporter")
    assert pkg.name == "weather-reporter"
    assert (Path(pkg.root_dir) / "SKILL.md").exists()


def test_skills_state_environment_variable_override(tmp_path: Path, monkeypatch):
    """環境変数 EDD_SKILLS_PATH による追加探索パスの解決を検証。"""
    extra_dir = tmp_path / "extra_skills_dir"
    extra_dir.mkdir()

    SkillScaffolder.scaffold("extra-analyzer", output_base_dir=extra_dir, pattern="reference")

    monkeypatch.setenv("EDD_SKILLS_PATH", str(extra_dir))

    state = SkillsState(project_root=tmp_path)
    skills = state.scan_skills()

    assert "extra-analyzer" in skills
