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
    """

    def __init__(
        self,
        skills_root: Optional[Union[str, Path]] = None,
        state: Optional[SkillsState] = None,
        min_tier: int = 1,
        include_system_skills: Optional[Set[str]] = None,
        additional_tools: Optional[List[Any]] = None,
        tool_name_prefix: Optional[str] = None,
        code_executor: Optional[Any] = None
    ):
        self.state = state or (SkillsState(skills_roots=[Path(skills_root)]) if skills_root else SkillsState())
        self.registry = EddSkillRegistry(state=self.state, min_tier=min_tier)
        self.min_tier = min_tier
        self.system_skills = include_system_skills or {"skill-creator", "skill-evolver"}

        # 事前ロード対象スキルの選定
        preloaded_skills = load_adk_skills_from_state(
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
            skills=preloaded_skills,
            registry=self.registry,
            code_executor=code_executor,
            additional_tools=additional_tools,
            tool_name_prefix=tool_name_prefix
        )

    # =========================================================================
    # 同期呼び出し用明示的ヘルパーメソッド（CLI、テスト、および同期スクリプト向け）
    # ※ ADK 純正メソッド（非同期ツール等）と名前衝突・モンキーパッチを回避
    # =========================================================================

    def list_skills_sync(self) -> List[Dict[str, Any]]:
        """利用可能な全スキルの Level 1 Frontmatter（name, description, tier）を返します。"""
        res = []
        for s in self.state.list_skills():
            t_val = s.tier.value if hasattr(s.tier, "value") else int(s.tier or 0)
            t_name = s.tier.name if hasattr(s.tier, "name") else (f"Tier {s.tier}" if s.tier else "Unranked")
            res.append({
                "name": s.name,
                "description": s.description,
                "tier": t_val,
                "tier_name": t_name,
                "path": s.root_dir
            })
        return res

    def search_skills_sync(self, query: str) -> List[Dict[str, Any]]:
        """クエリに基づいて関連するスキルを検索します。"""
        q = query.lower()
        matches = []
        for s in self.state.list_skills():
            if q in s.name.lower() or q in s.description.lower():
                t_val = s.tier.value if hasattr(s.tier, "value") else int(s.tier or 0)
                matches.append({
                    "name": s.name,
                    "description": s.description,
                    "tier": t_val
                })
        return matches

    def load_skill_sync(self, skill_name: str) -> Dict[str, Any]:
        """指定されたスキルの Level 2（SKILL.md 本文）を返します。"""
        skill = self.state.get_skill(skill_name)
        if not skill or not skill.root_dir:
            return {"status": "error", "message": f"Skill '{skill_name}' not found."}

        skill_md_path = Path(skill.root_dir) / "SKILL.md"
        if not skill_md_path.exists():
            return {"status": "error", "message": f"SKILL.md not found at {skill_md_path}."}

        return {
            "name": skill.name,
            "skill_md": skill_md_path.read_text(encoding="utf-8"),
            "status": "loaded"
        }

    def load_skill_resource_sync(self, skill_name: str, resource_rel_path: str) -> Dict[str, Any]:
        """指定されたスキルの Level 3 リソースを返します。"""
        skill = self.state.get_skill(skill_name)
        if not skill or not skill.root_dir:
            return {"status": "error", "message": f"Skill '{skill_name}' not found."}

        target_path = (Path(skill.root_dir) / resource_rel_path).resolve()
        if not target_path.exists():
            return {"status": "error", "message": f"Resource '{resource_rel_path}' not found in skill '{skill_name}'."}

        try:
            return {
                "status": "success",
                "skill_name": skill_name,
                "resource_path": resource_rel_path,
                "content": target_path.read_text(encoding="utf-8")
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to read resource '{resource_rel_path}': {e}"}

    def run_skill_script_sync(
        self,
        skill_name: str,
        script_name: Optional[str] = None,
        args: Optional[List[str]] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """スキルの決定論的スクリプトを同期実行します。"""
        skill = self.state.get_skill(skill_name)
        if not skill or not skill.root_dir:
            return {"status": "error", "message": f"Skill '{skill_name}' not found."}

        root_dir = Path(skill.root_dir)
        scripts_dir = root_dir / "scripts"
        if not scripts_dir.exists():
            return {"status": "error", "message": f"Scripts directory not found in skill '{skill_name}'."}

        target_script = file_path or script_name
        script_path = None
        if target_script:
            if target_script.startswith("scripts/"):
                target_script = target_script[len("scripts/"):]
            cand = scripts_dir / target_script
            if cand.exists():
                script_path = cand
            else:
                cand_py = scripts_dir / f"{target_script}.py"
                if cand_py.exists():
                    script_path = cand_py

        if not script_path:
            cand1 = scripts_dir / f"{skill_name.replace('-', '_')}.py"
            cand2 = scripts_dir / f"{skill_name}.py"
            cand3 = scripts_dir / "main.py"
            cand4 = scripts_dir / "run.py"
            for c in [cand1, cand2, cand3, cand4]:
                if c.exists():
                    script_path = c
                    break

        if not script_path:
            py_files = [f for f in scripts_dir.glob("*.py") if f.name != "__init__.py"]
            if len(py_files) == 1:
                script_path = py_files[0]

        if not script_path:
            return {"status": "error", "message": f"Could not resolve execution script in '{scripts_dir}'."}

        cmd = [sys.executable, str(script_path)] + (args or [])
        env = os.environ.copy()
        env["EDD_SKILL_NAME"] = skill_name
        env["EDD_SKILL_ROOT"] = str(root_dir)

        try:
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
            return {
                "status": "success" if proc.returncode == 0 else "failed",
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "script_path": str(script_path)
            }
        except Exception as e:
            return {
                "status": "error",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "script_path": str(script_path)
            }


def load_adk_skills_from_state(
    skills_dir: Optional[Union[str, Path]] = None,
    state: Optional[SkillsState] = None,
    min_tier: int = 1,
    include_system_skills: Optional[Set[str]] = None
) -> List[Skill]:
    """
    Google ADK 2.0 の load_skill_from_dir を用い、SkillsState でフィルタリングされた Skill モデルのリストを生成します。
    """
    resolved_state = state or (SkillsState(skills_roots=[Path(skills_dir)]) if skills_dir else SkillsState())
    system_skills = include_system_skills or {"skill-creator", "skill-evolver"}

    loaded_skills = []
    for skill_meta in resolved_state.list_skills():
        tier_val = skill_meta.tier.value if hasattr(skill_meta.tier, "value") else int(skill_meta.tier or 0)
        if tier_val < min_tier and skill_meta.name not in system_skills:
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
        additional_tools=additional_tools,
        tool_name_prefix=tool_name_prefix,
        code_executor=code_executor
    )
