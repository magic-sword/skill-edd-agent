"""
Tests for skill packaging and portability across all skills (including meta-skills).
"""

import os
import zipfile
import pytest
from pathlib import Path

from edd_agent_tools.skills.cli import package_skill_cli
from edd_agent_tools.validation.validator import SkillValidator


@pytest.mark.parametrize("skill_name", ["case-converter", "skill-creator", "skill-evolver"])
def test_all_skills_packaging_and_zip_integrity(skill_name: str, tmp_path: Path):
    """全てのスキル（メタスキル含む）が静的検証をパスし、配布用 ZIP に正常にパッケージ化されることを検証。"""
    skill_dir = Path("/workspace/src/skills") / skill_name
    assert skill_dir.exists(), f"Skill directory not found: {skill_dir}"

    # 1. 静的検証の事前チェック
    val_res = SkillValidator.validate_directory(skill_dir)
    assert val_res.is_valid is True, f"Validation failed for {skill_name}: {val_res.errors}"

    # 2. 配布用 ZIP パッケージ化
    out_dir = tmp_path / "dist"
    zip_path = package_skill_cli(str(skill_dir), output_dir_str=str(out_dir))

    assert zip_path is not None
    assert zip_path.exists()
    assert zip_path.suffix == ".zip"

    # 3. ZIP アーカイブの内容物整合性検査
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        # SKILL.md がルートまたはスキル名直下に存在するか確認
        has_skill_md = any(name.endswith("SKILL.md") for name in namelist)
        assert has_skill_md is True, f"Missing SKILL.md in {zip_path}"

        # scripts が存在する場合は scripts/ 配下のファイルが含まれているか確認
        if (skill_dir / "scripts").exists() and any((skill_dir / "scripts").glob("*.py")):
            has_scripts = any("scripts/" in name for name in namelist)
            assert has_scripts is True, f"Missing scripts/ in {zip_path}"
