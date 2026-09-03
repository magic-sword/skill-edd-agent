"""
Google ADK 2.0 Native SkillToolset & SkillRegistry Integration for EDD Agent Tools

Google Agent Development Kit (ADK) 2.0 の仕様（SkillToolset, SkillRegistry, load_skill_from_dir）に
100% 準拠したランタイム統合レイヤー。
"""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set

from google.adk.skills.models import Skill, Frontmatter, Resources, Script
from google.adk.skills import load_skill_from_dir
from google.adk.skills.skill_registry import SkillRegistry
from google.adk.tools.skill_toolset import SkillToolset

from edd_agent_tools.models.spec import SkillSpec
from edd_agent_tools.models.state import SkillTier
from edd_agent_tools.state import SkillsState


class EddSkillRegistry(SkillRegistry):
    """
    Google ADK 2.0 SkillRegistry を実装した EDD スキルレジストリ。
    SkillsState をバックエンドとして、Tier 状態、DAG 整合性、ローカルファイルシステムからの
    オンデマンドなスキル解決・検索を提供します。
    """

    def __init__(
        self,
        state: Optional[SkillsState] = None,
        skills_roots: Optional[List[Union[str, Path]]] = None,
        min_tier: int = 0
    ):
        if state:
            self.state = state
        elif skills_roots:
            self.state = SkillsState(skills_roots=[Path(p) for p in skills_roots])
        else:
            self.state = SkillsState()
        self.min_tier = min_tier

    async def get_skill(self, *, name: str) -> Skill:
        """指定された名前のスキルをロードして返します。"""
        skill_meta = self.state.get_skill(name)
        if not skill_meta or not skill_meta.root_dir:
            raise FileNotFoundError(f"Skill '{name}' not found in registry.")

        skill_dir = Path(skill_meta.root_dir)
        if not skill_dir.exists():
            raise FileNotFoundError(f"Skill directory not found at: {skill_dir}")

        return load_skill_from_dir(skill_dir)

    async def search_skills(self, *, query: str) -> List[Frontmatter]:
        """クエリに合致するスキルの Frontmatter 一覧を検索して返します。"""
        q = query.lower()
        results = []
        for s in self.state.list_skills():
            t_val = s.tier.value if hasattr(s.tier, "value") else int(s.tier or 0)
            if t_val < self.min_tier:
                continue
            if q in s.name.lower() or q in s.description.lower():
                results.append(Frontmatter(
                    name=s.name,
                    description=s.description,
                    metadata={
                        "tier": t_val,
                        "path": s.root_dir,
                        "pattern": str(s.pattern.value if hasattr(s.pattern, "value") else s.pattern)
                    }
                ))
        return results

    def search_tool_description(self) -> str | None:
        return "Search available skills in the local EDD skill registry by keyword, capability, or domain workflow."


class EddSkillToolset(SkillToolset):
    """
    Google ADK 2.0 純正の SkillToolset を継承した統合 Toolset クラス。
    EDD の Tier 状態管理および動的レジストリと完全統合されています。

    Google ADK 2.0 の Progressive Disclosure（段階的情報開示）仕様に完全準拠：
    - L1 (Metadata): 初期化時に登録された全スキルの名前・説明が list_skills またはプロンプト経由で開示。
    - L2 (Instructions): エージェントが必要と判断して load_skill を呼び出した際に SKILL.md 本文が開示。
    - L3 (Resources): 必要に応じて load_skill_resource や run_skill_script で決定論的スクリプト/資料が開示・実行。
    - Dynamic Registry: 登録外の外部・追加スキルも EddSkillRegistry (search_skills) 経由で動的探索・解決可能。
    """

    def __init__(
        self,
        skills_root: Optional[Union[str, Path]] = None,
        state: Optional[SkillsState] = None,
        min_tier: int = 1,
        include_system_skills: Optional[Set[str]] = None,
        registry_min_tier: int = 0,
        additional_tools: Optional[List[Any]] = None,
        tool_name_prefix: Optional[str] = None,
        code_executor: Optional[Any] = None
    ):
        self.state = state or (SkillsState(skills_roots=[Path(skills_root)]) if skills_root else SkillsState())
        self.registry = EddSkillRegistry(state=self.state, min_tier=registry_min_tier)
        self.min_tier = min_tier
        self.system_skills = include_system_skills or {"skill-creator", "skill-evolver"}

        # ADK 2.0 Progressive Disclosure: Tier基準を満たすローカルスキルを登録
        # （L1 Frontmatterがlist_skillsで開示され、L2/L3はload_skill/run_skill_scriptでオンデマンド開示）
        registered_skills = load_adk_skills_from_state(
            state=self.state,
            min_tier=min_tier,
            include_system_skills=self.system_skills
        )

        # コードエグゼキュータのデフォルト解決（ADK公式のUnsafeLocalCodeExecutorを利用）
        if code_executor is None:
            try:
                from google.adk.code_executors import UnsafeLocalCodeExecutor
                code_executor = UnsafeLocalCodeExecutor()
            except Exception:
                code_executor = None

        super().__init__(
            skills=registered_skills,
            registry=self.registry,
            code_executor=code_executor,
            additional_tools=additional_tools,
            tool_name_prefix=tool_name_prefix
        )

    # EddSkillToolset inherits all official tools (ListSkillsTool, LoadSkillTool,
    # LoadSkillResourceTool, RunSkillScriptTool, SearchSkillsTool) directly from ADK 2.0 SkillToolset.




def load_adk_skills_from_state(
    skills_dir: Optional[Union[str, Path]] = None,
    state: Optional[SkillsState] = None,
    min_tier: int = 1,
    include_system_skills: Optional[Set[str]] = None
) -> List[Skill]:
    """
    Google ADK 2.0 の load_skill_from_dir を用い、SkillsState でフィルタリングされた Skill モデルのリストを生成します。
    ADK 2.0 の Progressive Disclosure に従い、min_tier 以上のスキルおよび必須システムスキルを登録対象とします。
    """
    resolved_state = state or (SkillsState(skills_roots=[Path(skills_dir)]) if skills_dir else SkillsState())
    system_skills = include_system_skills or {"skill-creator", "skill-evolver"}

    loaded_skills = []
    for skill_meta in resolved_state.list_skills():
        tier_val = skill_meta.tier.value if hasattr(skill_meta.tier, "value") else int(skill_meta.tier or 0)
        
        # システムスキルまたは min_tier 以上のスキルを登録対象とする
        if skill_meta.name not in system_skills and tier_val < min_tier:
            continue

        skill_path = Path(skill_meta.root_dir) if skill_meta.root_dir and Path(skill_meta.root_dir).exists() else None
        if skill_path and (skill_path / "SKILL.md").exists():
            try:
                adk_skill = load_skill_from_dir(skill_path)
                loaded_skills.append(adk_skill)
            except Exception as e:
                print(f"Warning: Failed to load ADK skill '{skill_meta.name}': {e}", file=sys.stderr)

    return loaded_skills


def create_adk_skill_toolset(
    skills_dir: Optional[Union[str, Path]] = None,
    state: Optional[SkillsState] = None,
    min_tier: int = 1,
    include_system_skills: Optional[Set[str]] = None,
    registry_min_tier: int = 0,
    additional_tools: Optional[List[Any]] = None,
    tool_name_prefix: Optional[str] = None,
    code_executor: Optional[Any] = None
) -> EddSkillToolset:
    """
    Google ADK 2.0 純正仕様に完全準拠した EddSkillToolset インスタンスを生成して返します。
    """
    return EddSkillToolset(
        skills_root=skills_dir,
        state=state,
        min_tier=min_tier,
        include_system_skills=include_system_skills,
        registry_min_tier=registry_min_tier,
        additional_tools=additional_tools,
        tool_name_prefix=tool_name_prefix,
        code_executor=code_executor
    )

