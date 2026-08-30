"""
Skill Template Engine for edd-agent-tools

Anthropic Claude Skills / Google ADK 2.0 準拠の SKILL.md レンダリングエンジン。
Markdown テンプレート（src/skills/skill-creator/assets/templates/）を単一真実源（SSOT）として
動的にロード・展開します。
"""

import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..models.draft import SkillLogicDraft
from ..models.spec import SkillPattern


class SkillTemplateEngine:
    """SkillLogicDraft から Anthropic 準拠の洗練された SKILL.md を決定論的にレンダリングするエンジン。
    
    テンプレート素材（assets/templates/*.md）を単一真実源（SSOT）として読み込み展開します。
    """

    @classmethod
    def title_case_skill_name(cls, skill_name: str) -> str:
        """ハイフンケースのスキル名を Title Case に変換"""
        return " ".join(word.capitalize() for word in skill_name.split("-"))

    @classmethod
    def load_raw_template(cls, pattern: SkillPattern | str, custom_templates_dir: Optional[str | Path] = None) -> Optional[str]:
        """`assets/templates/{pattern}_template.md` を探索・ロードします。"""
        pat_str = pattern.value if hasattr(pattern, "value") else str(pattern)
        
        cand_dirs = []
        if custom_templates_dir:
            cand_dirs.append(Path(custom_templates_dir).resolve())
        cand_dirs.extend([
            Path("src/skills/skill-creator/assets/templates"),
            Path("skills/skill-creator/assets/templates"),
            Path(".agents/skills/skill-creator/assets/templates"),
        ])

        for c_dir in cand_dirs:
            t_path = c_dir / f"{pat_str}_template.md"
            if t_path.exists():
                try:
                    return t_path.read_text(encoding="utf-8")
                except Exception:
                    pass
        return None

    @classmethod
    def render(cls, draft: SkillLogicDraft, custom_templates_dir: Optional[str | Path] = None) -> str:
        """SkillLogicDraft を受け取り、完全な SKILL.md 文字列を生成して返します。"""
        title = cls.title_case_skill_name(draft.name)
        lines = []

        # 1. YAML Frontmatter
        lines.append("---")
        lines.append(f"name: {draft.name}")
        desc_escaped = draft.description_third_person.replace("\n", " ").strip()
        lines.append(f"description: {desc_escaped}")
        lines.append("license: Complete terms in LICENSE.txt")
        pat_val = draft.pattern.value if hasattr(draft.pattern, "value") else str(draft.pattern)
        lines.append(f"pattern: {pat_val}")
        if draft.dependencies:
            lines.append("dependencies:")
            for dep in draft.dependencies:
                lines.append(f"  - {dep}")
        lines.append("---")
        lines.append("")

        # 2. Main Title & Overview
        lines.append(f"# {title}")
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        lines.append(draft.overview_summary.strip())
        lines.append("")

        # 3. Pattern-Specific Core Section
        if draft.pattern == SkillPattern.WORKFLOW:
            lines.extend(cls._render_workflow_section(draft))
        elif draft.pattern == SkillPattern.TASK_BASED:
            lines.extend(cls._render_task_based_section(draft))
        elif draft.pattern == SkillPattern.REFERENCE:
            lines.extend(cls._render_reference_section(draft))
        elif draft.pattern == SkillPattern.CAPABILITIES:
            lines.extend(cls._render_capabilities_section(draft))
        else:
            lines.extend(cls._render_workflow_section(draft))

        # 4. Trigger Scenarios & Concrete Examples
        lines.append("## Usage Scenarios & Trigger Examples")
        lines.append("")
        lines.append("This skill is triggered when handling requests such as:")
        lines.append("")
        for example in draft.concrete_trigger_examples:
            lines.append(f'- "{example.strip()}"')
        lines.append("")

        # 5. When NOT to Use This Skill (Negative Space Guidance)
        if draft.when_not_to_use:
            lines.append("## When NOT to Use This Skill")
            lines.append("")
            lines.append("Do NOT use this skill in the following scenarios (use native tools or alternative workflows instead):")
            lines.append("")
            for item in draft.when_not_to_use:
                lines.append(f"- {item.strip()}")
            lines.append("")

        # 6. Resources Section
        lines.extend(cls._render_resources_section(draft))

        # 7. Guidelines & Best Practices
        if draft.guidelines:
            lines.append("## Guidelines & Best Practices")
            lines.append("")
            for g in draft.guidelines:
                lines.append(f"- {g.strip()}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    @classmethod
    def _render_workflow_section(cls, draft: SkillLogicDraft) -> list[str]:
        lines = []
        if draft.decision_tree:
            lines.append("## Workflow Decision Tree")
            lines.append("")
            lines.append("To determine the appropriate procedure, follow this decision logic:")
            lines.append("")
            for branch in draft.decision_tree:
                lines.append(f"- **If** {branch.condition.strip()} ➔ **Then** {branch.action.strip()}")
            lines.append("")

        lines.append("## Step-by-Step Instructions")
        lines.append("")
        for step in draft.execution_steps:
            res_info = f" *(Target: `{step.target_resource}`)*" if step.target_resource else ""
            lines.append(f"### Step {step.step_number}: {step.title.strip()}{res_info}")
            lines.append("")
            lines.append(step.action_imperative.strip())
            lines.append("")
        return lines

    @classmethod
    def _render_task_based_section(cls, draft: SkillLogicDraft) -> list[str]:
        lines = []
        lines.append("## Quick Start")
        lines.append("")
        lines.append("Execute standard operations using the provided modular tools and scripts.")
        lines.append("")
        lines.append("## Available Tasks")
        lines.append("")
        for step in draft.execution_steps:
            res_info = f" *(Tool: `{step.target_resource}`)*" if step.target_resource else ""
            lines.append(f"### Task {step.step_number}: {step.title.strip()}{res_info}")
            lines.append("")
            lines.append(step.action_imperative.strip())
            lines.append("")
        return lines

    @classmethod
    def _render_reference_section(cls, draft: SkillLogicDraft) -> list[str]:
        lines = []
        lines.append("## Guidelines & Specifications")
        lines.append("")
        for step in draft.execution_steps:
            res_info = f" *(Reference: `{step.target_resource}`)*" if step.target_resource else ""
            lines.append(f"### {step.title.strip()}{res_info}")
            lines.append("")
            lines.append(step.action_imperative.strip())
            lines.append("")
        return lines

    @classmethod
    def _render_capabilities_section(cls, draft: SkillLogicDraft) -> list[str]:
        lines = []
        lines.append("## Core Capabilities")
        lines.append("")
        for step in draft.execution_steps:
            res_info = f" *(Module: `{step.target_resource}`)*" if step.target_resource else ""
            lines.append(f"### {step.step_number}. {step.title.strip()}{res_info}")
            lines.append("")
            lines.append(step.action_imperative.strip())
            lines.append("")
        return lines

    @classmethod
    def _render_resources_section(cls, draft: SkillLogicDraft) -> list[str]:
        lines = []
        lines.append("## Bundled Resources")
        lines.append("")

        scripts = [r for r in draft.resources_plan if r.type == "script" or r.rel_path.startswith("scripts/")]
        references = [r for r in draft.resources_plan if r.type == "reference" or r.rel_path.startswith("references/")]
        assets = [r for r in draft.resources_plan if r.type == "asset" or r.rel_path.startswith("assets/")]

        if scripts:
            lines.append("### `scripts/` (Executable Tools)")
            for s in scripts:
                lines.append(f"- **`{s.rel_path}`**: {s.purpose.strip()}")
            lines.append("")

        if references:
            lines.append("### `references/` (On-Demand Knowledge)")
            for r in references:
                lines.append(f"- **`{r.rel_path}`**: {r.purpose.strip()}")
            lines.append("")

        if assets:
            lines.append("### `assets/` (Output Templates & Boilerplates)")
            for a in assets:
                lines.append(f"- **`{a.rel_path}`**: {a.purpose.strip()}")
            lines.append("")

        return lines
