import pytest
import asyncio
from pathlib import Path
from google.adk.skills.models import Skill
from google.adk.tools.skill_toolset import SkillToolset
from edd_agent_tools.adk.toolset import EddSkillToolset, EddSkillRegistry, create_adk_skill_toolset
from edd_agent_tools.models.spec import SkillSpec


def test_adk_toolset_sync_helpers():
    """EddSkillToolset による同期ヘルパーメソッドをテストします。"""
    toolset = EddSkillToolset(skills_root="src/skills")
    skills = toolset.list_skills_sync()
    assert len(skills) > 0
    assert any(s["name"] == "case-converter" for s in skills)

    # 検索
    results = toolset.search_skills_sync("converter")
    assert len(results) >= 1
    assert results[0]["name"] == "case-converter"

    # ロード
    loaded = toolset.load_skill_sync("case-converter")
    assert loaded.get("status") == "loaded"
    assert "case_converter.py" in loaded.get("skill_md", "")

    # スクリプト実行
    res = toolset.run_skill_script_sync(
        skill_name="case-converter",
        args=["--input", "foo_bar_baz", "--format", "kebab"]
    )
    assert res.get("status") == "success"
    assert res.get("exit_code") == 0
    assert "foo-bar-baz" in res.get("stdout", "")


def test_adk_native_skill_registry():
    """EddSkillRegistry の非同期 get_skill と search_skills をテストします。"""
    async def _test():
        registry = EddSkillRegistry(skills_roots=["src/skills"])
        # search
        results = await registry.search_skills(query="converter")
        assert len(results) >= 1
        assert results[0].name == "case-converter"

        # get
        skill = await registry.get_skill(name="case-converter")
        assert isinstance(skill, Skill)
        assert skill.name == "case-converter"
        assert "scripts/case_converter.py" in skill.instructions or "case_converter" in skill.instructions

    asyncio.run(_test())


def test_adk_native_skillset_creation():
    """create_adk_skill_toolset が ADK 純正の SkillToolset を生成することをテストします。"""
    toolset = create_adk_skill_toolset(skills_dir="src/skills")
    assert isinstance(toolset, SkillToolset)
    tool_names = [t.name for t in toolset._tools]
    assert "list_skills" in tool_names
    assert "load_skill" in tool_names
    assert "load_skill_resource" in tool_names
    assert "run_skill_script" in tool_names
    assert "search_skills" in tool_names


def test_skill_spec_adk_conversion():
    """SkillSpec と google.adk.skills.models.Skill の双方向変換をテストします。"""
    spec_path = Path("src/skills/case-converter/SKILL.md")
    spec = SkillSpec.load_from_file(spec_path)

    # to_adk_skill
    adk_skill = spec.to_adk_skill(skill_dir="src/skills/case-converter")
    assert isinstance(adk_skill, Skill)
    assert adk_skill.name == "case-converter"
    assert "case_converter.py" in adk_skill.resources.scripts

    # from_adk_skill
    roundtrip_spec = SkillSpec.from_adk_skill(adk_skill)
    assert roundtrip_spec.name == "case-converter"
    assert roundtrip_spec.frontmatter.description == spec.frontmatter.description


def test_core_skill_adk_properties():
    """core.Skill ドメインエンティティが ADK 純正モデルと透過的に連携することをテストします。"""
    from edd_agent_tools.core import Skill as CoreSkill
    skill = CoreSkill("src/skills/case-converter")
    assert skill.name == "case-converter"
    assert skill.frontmatter.name == "case-converter"
    assert skill.instructions is not None
    assert "case_converter.py" in skill.resources.scripts
    adk_skill = skill.to_adk_skill()
    assert isinstance(adk_skill, Skill)


def test_adk_toolset_file_path_execution():
    """EddSkillToolset が file_path 引数によるスクリプト実行をサポートすることをテストします。"""
    toolset = EddSkillToolset(skills_root="src/skills")
    res = toolset.run_skill_script_sync(
        skill_name="case-converter",
        file_path="scripts/case_converter.py",
        args=["--input", "hello_world_test", "--format", "pascal"]
    )
    assert res.get("status") == "success"
    assert res.get("exit_code") == 0
    assert "HelloWorldTest" in res.get("stdout", "")


def test_adk_frontmatter_extended_fields_roundtrip():
    """allowed-tools, compatibility, metadata を含む Frontmatter の双方向変換をテストします。"""
    content = """---
name: sample-extended-skill
description: Tests extended ADK frontmatter fields. Use when validating frontmatter compatibility.
license: Apache-2.0
compatibility: python>=3.10
allowed-tools:
  - run_skill_script
  - bash
metadata:
  category: utility
  author: test-suite
---

# Sample Extended Skill
## Overview
Sample overview text.
"""
    spec = SkillSpec.parse_markdown(content)
    assert spec.frontmatter.compatibility == "python>=3.10"
    assert spec.frontmatter.allowed_tools == ["run_skill_script", "bash"]
    assert spec.frontmatter.metadata.get("category") == "utility"

    # ADK Skill への変換
    adk_skill = spec.to_adk_skill()
    assert adk_skill.frontmatter.compatibility == "python>=3.10"
    assert "run_skill_script" in adk_skill.frontmatter.allowed_tools
    assert adk_skill.frontmatter.metadata.get("author") == "test-suite"

    # ADK Skill からの復元
    roundtrip = SkillSpec.from_adk_skill(adk_skill)
    assert roundtrip.frontmatter.compatibility == "python>=3.10"
    assert "run_skill_script" in str(roundtrip.frontmatter.allowed_tools)
    assert roundtrip.frontmatter.metadata.get("category") == "utility"


