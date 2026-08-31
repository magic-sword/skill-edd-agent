import os
import shutil
import pytest
import subprocess
import sys
from pathlib import Path
from edd_agent_tools import Skill, SkillValidator, SkillScaffolder, SkillPackager


@pytest.fixture
def temp_output_dir(tmp_path):
    out_dir = tmp_path / "skills_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def test_package_level_skill_scaffolder_and_cascading(temp_output_dir):
    """edd-agent-tools パッケージ側の SkillScaffolder による雛形生成・カスケード解決テスト"""
    target_dir = SkillScaffolder.scaffold(
        skill_name="text-analyzer",
        output_base_dir=temp_output_dir,
        pattern="workflow"
    )

    assert target_dir.exists()
    assert (target_dir / "SKILL.md").exists()

    # 静的バリデーションの検証
    val_res = SkillValidator.validate_directory(target_dir)
    assert val_res.is_valid is True
    assert len(val_res.errors) == 0

    # 生成されたスキルを Skill ドメインクラスでロード
    generated_skill = Skill(root_dir=str(target_dir), tier=1)
    assert generated_skill.name == "text-analyzer"
    assert len(generated_skill.list_scripts()) >= 1


def test_skill_creator_meta_skill_structure_and_validation():
    """src/skills/skill-creator のメタスキル構造と静的検証テスト"""
    creator_dir = Path("/workspace/src/skills/skill-creator")
    assert creator_dir.exists()
    assert (creator_dir / "SKILL.md").exists()
    assert (creator_dir / "assets" / "templates").exists()
    assert (creator_dir / "references" / "skill_design_guide.md").exists()

    # 静的検証（不要な scripts/ ラッパーがなく純化されていること）
    val_res = SkillValidator.validate_directory(creator_dir)
    assert val_res.is_valid is True
    assert len(val_res.errors) == 0
