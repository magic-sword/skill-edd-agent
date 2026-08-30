import pytest
from pathlib import Path
from edd_agent_tools.adk.toolset import EddSkillToolset


def test_adk_toolset_list_and_search():
    """EddSkillToolset による list_skills および search_skills をテストします。"""
    toolset = EddSkillToolset(skills_root="src/skills")
    skills = toolset.list_skills()
    assert len(skills) > 0
    assert any(s["name"] == "case-converter" for s in skills)

    # 検索
    results = toolset.search_skills("converter")
    assert len(results) >= 1
    assert results[0]["name"] == "case-converter"


def test_adk_toolset_load_skill():
    """EddSkillToolset による load_skill (Level 2 SKILL.md 展開) をテストします。"""
    toolset = EddSkillToolset(skills_root="src/skills")
    loaded = toolset.load_skill("case-converter")
    assert loaded.get("status") == "loaded"
    assert "case-converter" in loaded.get("name", "")
    assert "SKILL.md" in loaded or "skill_md" in loaded
    assert "case_converter.py" in loaded.get("skill_md", "")


def test_adk_toolset_run_skill_script():
    """EddSkillToolset による run_skill_script (Level 3 スクリプト実行) をテストします。"""
    toolset = EddSkillToolset(skills_root="src/skills")
    res = toolset.run_skill_script(
        skill_name="case-converter",
        args=["--input", "foo_bar_baz", "--format", "kebab"]
    )
    assert res.get("status") == "success"
    assert res.get("exit_code") == 0
    assert "foo-bar-baz" in res.get("stdout", "")
