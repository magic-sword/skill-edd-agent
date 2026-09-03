import pytest
import asyncio
from pathlib import Path
from google.adk.skills.models import Skill
from google.adk.tools.skill_toolset import SkillToolset
from edd_agent_tools.adk.toolset import EddSkillToolset, EddSkillRegistry, create_adk_skill_toolset
from edd_agent_tools.models.spec import SkillSpec


def test_adk_toolset_native_tools_execution():
    """EddSkillToolset が提供する ADK 公式ツール群の非同期実行をテストします。"""
    async def _test():
        from unittest.mock import MagicMock
        ctx = MagicMock()
        ctx.invocation_id = "test-inv-001"
        ctx.state = {}

        toolset = create_adk_skill_toolset(skills_dir="src/skills")
        tools_dict = {t.name: t for t in toolset._tools}
        assert "run_skill_script" in tools_dict
        assert "load_skill" in tools_dict
        assert "list_skills" in tools_dict

        # load_skill ツールの実行
        load_tool = tools_dict["load_skill"]
        load_res = await load_tool.run_async(args={"skill_name": "case-converter"}, tool_context=ctx)
        assert load_res.get("skill_name") == "case-converter"
        assert "case_converter.py" in load_res.get("instructions", "")

    asyncio.run(_test())


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
    """SkillPackage が file_path 引数によるスクリプト実行をサポートすることをテストします。"""
    from edd_agent_tools.core import SkillPackage
    pkg = SkillPackage("src/skills/case-converter")
    res = pkg.execute_script(
        script_name="scripts/case_converter.py",
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


def test_adk_progressive_disclosure_registry_resolution():
    """ADK 2.0 公式 Progressive Disclosure: ローカルスキルの list_skills による開示と、未登録スキルの search_skills / load_skill 動的解決をテストします。"""
    async def _test():
        from unittest.mock import MagicMock
        ctx = MagicMock()
        ctx.invocation_id = "test-inv-prog-001"
        ctx.state = {}

        # 1. min_tier=1 (標準構成): Tier 1 以上のスキルがローカル登録され、list_skills で一覧開示される
        toolset_local = create_adk_skill_toolset(skills_dir="src/skills", min_tier=1)
        assert "case-converter" in toolset_local._skills
        assert "skill-creator" in toolset_local._skills

        list_tool = next(t for t in toolset_local._tools if t.name == "list_skills")
        list_res = await list_tool.run_async(args={}, tool_context=ctx)
        assert "case-converter" in list_res
        assert "skill-creator" in list_res

        # 2. 未登録スキル (min_tier=3等でローカル除外されたスキル): search_skills でレジストリから検索され、load_skill でオンデマンド解決される
        toolset_dynamic = create_adk_skill_toolset(
            skills_dir="src/skills",
            min_tier=3,
            include_system_skills={"skill-creator"}
        )
        assert "case-converter" not in toolset_dynamic._skills

        search_tool = next(t for t in toolset_dynamic._tools if t.name == "search_skills")
        search_res = await search_tool.run_async(args={"query": "converter"}, tool_context=ctx)
        assert any(r.get("name") == "case-converter" for r in search_res)

        # 3. load_skill ツールにより、レジストリ経由で未登録スキルの手順書（L2 Instructions）がオンデマンドにロードされる
        load_tool = next(t for t in toolset_dynamic._tools if t.name == "load_skill")
        load_res = await load_tool.run_async(args={"skill_name": "case-converter"}, tool_context=ctx)
        assert load_res.get("skill_name") == "case-converter"
        assert "case_converter.py" in load_res.get("instructions", "")

    asyncio.run(_test())


def test_adk_criteria_type_safety():
    """AdkEvalAdapter.build_eval_config が型安全な専用 Criterion クラスを生成することをテストします。"""
    from edd_agent_tools.evaluation.adk_eval import AdkEvalAdapter
    from google.adk.evaluation.eval_metrics import ToolTrajectoryCriterion, RubricsBasedCriterion

    # デフォルト設定での構築
    config = AdkEvalAdapter.build_eval_config(default_trajectory_mode="in_order")
    assert "tool_trajectory_avg_score" in config.criteria
    traj_crit = config.criteria["tool_trajectory_avg_score"]
    assert isinstance(traj_crit, ToolTrajectoryCriterion)
    assert traj_crit.match_type == ToolTrajectoryCriterion.MatchType.IN_ORDER

    # ルーブリック基準を含む明示的指定での構築
    explicit_criteria = {
        "tool_trajectory_avg_score": {
            "threshold": 1.0,
            "match_type": "EXACT"
        },
        "rubric_based_final_response_quality_v1": {
            "threshold": 0.8,
            "rubrics": [
                {"rubric_id": "r1", "rubric_content": {"text_property": "Accurate output"}}
            ]
        }
    }
    config2 = AdkEvalAdapter.build_eval_config(criteria=explicit_criteria)
    assert isinstance(config2.criteria["tool_trajectory_avg_score"], ToolTrajectoryCriterion)
    assert config2.criteria["tool_trajectory_avg_score"].match_type == ToolTrajectoryCriterion.MatchType.EXACT
    assert isinstance(config2.criteria["rubric_based_final_response_quality_v1"], RubricsBasedCriterion)



