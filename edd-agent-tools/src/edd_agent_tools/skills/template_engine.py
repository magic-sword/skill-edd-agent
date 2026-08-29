import os
from typing import Optional
from string import Template
from .models import SkillLogicDraft, SkillPattern

class SkillTemplateEngine:
    """SkillLogicDraft から Anthropic 準拠の洗練された SKILL.md を決定論的にレンダリングするエンジン"""

    @classmethod
    def title_case_skill_name(cls, skill_name: str) -> str:
        """ハイフンケースのスキル名を Title Case に変換"""
        return " ".join(word.capitalize() for word in skill_name.split("-"))

    @classmethod
    def render(cls, draft: SkillLogicDraft) -> str:
        """SkillLogicDraft を受け取り、完全な SKILL.md 文字列を生成して返します。"""
        title = cls.title_case_skill_name(draft.name)
        lines = []

        # 1. YAML Frontmatter
        lines.append("---")
        lines.append(f"name: {draft.name}")
        # description 内の改行や特殊文字を安全にエスケープ
        desc_escaped = draft.description_third_person.replace("\n", " ").strip()
        lines.append(f"description: {desc_escaped}")
        lines.append("license: Complete terms in LICENSE.txt")
        lines.append(f"pattern: {draft.pattern.value}")
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

        # 5. Resources Section
        lines.extend(cls._render_resources_section(draft))

        # 6. Guidelines & Best Practices
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
        if not draft.resources_plan:
            lines.append("This skill operates directly via standard instructions without bundled external files.")
            lines.append("")
            return lines

        scripts = [r for r in draft.resources_plan if r.type == "script"]
        references = [r for r in draft.resources_plan if r.type == "reference"]
        assets = [r for r in draft.resources_plan if r.type == "asset"]

        if scripts:
            lines.append("### `scripts/` (Executable Tools)")
            lines.append("Deterministic execution scripts that run directly in the environment:")
            lines.append("")
            for s in scripts:
                lines.append(f"- **`{s.rel_path}`**: {s.purpose.strip()}")
            lines.append("")

        if references:
            lines.append("### `references/` (On-Demand Knowledge)")
            lines.append("Documentation and schema specifications loaded only when explicitly needed:")
            lines.append("")
            for r in references:
                lines.append(f"- **`{r.rel_path}`**: {r.purpose.strip()}")
            lines.append("")

        if assets:
            lines.append("### `assets/` (Output Templates & Boilerplates)")
            lines.append("Template files and assets copied or utilized in the output:")
            lines.append("")
            for a in assets:
                lines.append(f"- **`{a.rel_path}`**: {a.purpose.strip()}")
            lines.append("")

        return lines
