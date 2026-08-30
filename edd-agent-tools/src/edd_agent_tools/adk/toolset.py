"""
Google ADK 2.0 SkillToolset Adapter for EDD Agent Tools

Google Agent Development Kit (ADK) 2.0 互換の SkillToolset 実装およびファクトリ。
Markdown-First & Progressive Disclosure に基づくライフサイクル
(list_skills, load_skill, load_skill_resource, run_skill_script) を提供します。
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set

from edd_agent_tools.models.spec import SkillSpec
from edd_agent_tools.models.state import SkillTier
from edd_agent_tools.state import SkillsState


class EddSkillToolset:
    """
    Google ADK 2.0 互換の SkillToolset クラス。
    エージェントに対してスキルの探索、ロード、リソース読み込み、および決定論的スクリプト実行ツールを提供します。
    """

    def __init__(
        self,
        skills_root: Optional[Union[str, Path]] = None,
        state: Optional[SkillsState] = None
    ):
        self.skills_root = Path(skills_root).resolve() if skills_root else None
        if state:
            self.state = state
        elif self.skills_root:
            self.state = SkillsState(skills_roots=[self.skills_root])
        else:
            self.state = SkillsState()

    def list_skills(self) -> List[Dict[str, Any]]:
        """利用可能な全スキルの Level 1 Frontmatter（name, description, tier）を返します。"""
        skills = self.state.list_skills()
        res = []
        for s in skills:
            t_val = s.tier.value if hasattr(s.tier, "value") else (int(s.tier) if s.tier else 0)
            t_name = s.tier.name if hasattr(s.tier, "name") else (f"Tier {s.tier}" if s.tier else "Unranked")
            res.append({
                "name": s.name,
                "description": s.description,
                "tier": t_val,
                "tier_name": t_name,
                "path": s.root_dir
            })
        return res

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """クエリに基づいて関連するスキルを検索します。"""
        q = query.lower()
        skills = self.state.list_skills()
        matches = []
        for s in skills:
            if q in s.name.lower() or q in s.description.lower():
                t_val = s.tier.value if hasattr(s.tier, "value") else (int(s.tier) if s.tier else 0)
                matches.append({
                    "name": s.name,
                    "description": s.description,
                    "tier": t_val
                })
        return matches

    def load_skill(self, skill_name: str) -> Dict[str, Any]:
        """
        指定されたスキルの Level 2（SKILL.md 本文、意思決定ツリー、手順）を展開して返します。
        エージェントのコンテキスト（System Prompt）に注入するために使用します。
        """
        skill = self.state.get_skill(skill_name)
        if not skill:
            # ファイルシステム直接探索
            if self.skills_root:
                cand = self.skills_root / skill_name / "SKILL.md"
                if cand.exists():
                    return {
                        "name": skill_name,
                        "skill_md": cand.read_text(encoding="utf-8"),
                        "status": "loaded"
                    }
            return {
                "status": "error",
                "message": f"Skill '{skill_name}' not found."
            }

        skill_md_path = Path(skill.spec_path)
        if not skill_md_path.exists():
            return {
                "status": "error",
                "message": f"SKILL.md not found at {skill_md_path}."
            }

        return {
            "name": skill.spec.name,
            "skill_md": skill_md_path.read_text(encoding="utf-8"),
            "spec": skill.spec.model_dump(),
            "status": "loaded"
        }

    def load_skill_resource(self, skill_name: str, resource_rel_path: str) -> Dict[str, Any]:
        """
        指定されたスキルの Level 3 リソース（references/*, assets/*）をオンデマンドで読み込みます。
        """
        skill = self.state.get_skill(skill_name)
        root_dir = Path(skill.root_dir) if skill else (self.skills_root / skill_name if self.skills_root else Path(skill_name))

        target_path = (root_dir / resource_rel_path).resolve()
        if not target_path.exists():
            return {
                "status": "error",
                "message": f"Resource '{resource_rel_path}' not found in skill '{skill_name}'."
            }

        try:
            content = target_path.read_text(encoding="utf-8")
            return {
                "status": "success",
                "skill_name": skill_name,
                "resource_path": resource_rel_path,
                "content": content
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read resource '{resource_rel_path}': {e}"
            }

    def run_skill_script(
        self,
        skill_name: str,
        script_name: Optional[str] = None,
        args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        スキルの決定論的スクリプト（scripts/*.py）を動的ディスパッチ実行します。
        """
        skill = self.state.get_skill(skill_name)
        root_dir = Path(skill.root_dir) if skill else (self.skills_root / skill_name if self.skills_root else Path(skill_name))
        scripts_dir = root_dir / "scripts"

        if not scripts_dir.exists():
            return {
                "status": "error",
                "message": f"Scripts directory not found in skill '{skill_name}'."
            }

        script_path = None
        if script_name:
            cand = scripts_dir / script_name
            if cand.exists():
                script_path = cand
            else:
                cand_py = scripts_dir / f"{script_name}.py"
                if cand_py.exists():
                    script_path = cand_py

        if not script_path:
            # デフォルト検出
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
            return {
                "status": "error",
                "message": f"Could not resolve execution script in '{scripts_dir}'."
            }

        cmd = [sys.executable, str(script_path)] + (args or [])
        env = os.environ.copy()
        env["EDD_SKILL_NAME"] = skill_name
        env["EDD_SKILL_ROOT"] = str(root_dir)

        try:
            proc = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "status": "success" if proc.returncode == 0 else "failed",
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "script_path": str(script_path)
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "exit_code": -1,
                "stdout": "",
                "stderr": "Execution timed out after 60s",
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
) -> List[Any]:
    """
    Google ADK 2.0 の load_skill_from_dir を用い、SkillsState でフィルタリングされたスキルモデルのリストを生成します。
    """
    try:
        from google.adk.skills import load_skill_from_dir
    except ImportError:
        return []

    resolved_state = state or SkillsState()
    system_skills = include_system_skills or {"skill-creator", "skill-evolver"}
    resolved_skills_dir = Path(skills_dir).resolve() if skills_dir else Path("src/skills").resolve()

    loaded_skills = []
    for skill_meta in resolved_state.list_skills():
        tier_val = skill_meta.tier.value if hasattr(skill_meta.tier, "value") else int(skill_meta.tier or 0)
        if tier_val < min_tier and skill_meta.name not in system_skills:
            continue

        skill_path = Path(skill_meta.root_dir) if skill_meta.root_dir and Path(skill_meta.root_dir).exists() else (resolved_skills_dir / skill_meta.name)
        if skill_path.exists() and (skill_path / "SKILL.md").exists():
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
    include_system_skills: Optional[Set[str]] = None
) -> Any:
    """
    Google ADK 公式の SkillToolset インスタンスを生成して返します。
    """
    from google.adk.tools.skill_toolset import SkillToolset
    skills = load_adk_skills_from_state(
        skills_dir=skills_dir,
        state=state,
        min_tier=min_tier,
        include_system_skills=include_system_skills
    )
    return SkillToolset(skills=skills)
