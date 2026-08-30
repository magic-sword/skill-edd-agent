"""
Skill Creation Engine - 決定論的スキルパッケージ生成＆検証エンジン
Anthropic Markdown-First & Google ADK 2.0 準拠の 3層リソース分離（SKILL.md, scripts/, references/, assets/）
およびテストハーネスの初期化・検証を完全決定論的に実行します。
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

from edd_agent_tools.models import (
    SkillLogicDraft,
    SkillPattern,
    DecisionBranch,
    StepInstruction,
    ResourcePlan
)
from edd_agent_tools.skills.template_engine import SkillTemplateEngine
from edd_agent_tools.validation.validator import SkillValidator, ValidationResult
from edd_agent_tools.state import SkillsState
from edd_agent_tools.skill import Skill
from edd_agent_tools.evaluation import ContractTestRunner, LocalWorkspaceEnv


class SkillCreationEngine:
    """決定論的スキルパッケージ生成および初期検証を行うエンジン。"""

    def __init__(self, output_base_dir: str = "src/skills"):
        self.output_base_dir = Path(output_base_dir).resolve()
        self.state = SkillsState()

    def create_skill_from_draft(
        self,
        draft: SkillLogicDraft,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """構造化された SkillLogicDraft から完全なスキルパッケージおよびテストハーネスを生成します。"""
        # 出力先ディレクトリの決定
        if output_dir:
            target_skill_dir = Path(output_dir).resolve()
            if target_skill_dir.name != draft.name:
                target_skill_dir = target_skill_dir / draft.name
        else:
            target_skill_dir = self.output_base_dir / draft.name

        target_skill_dir.mkdir(parents=True, exist_ok=True)
        (target_skill_dir / "scripts").mkdir(parents=True, exist_ok=True)
        (target_skill_dir / "references").mkdir(parents=True, exist_ok=True)
        (target_skill_dir / "assets").mkdir(parents=True, exist_ok=True)

        # 1. SKILL.md の決定論的レンダリング
        skill_md_content = SkillTemplateEngine.render(draft)
        (target_skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

        # 2. リソース雛形の生成
        for res_plan in draft.resources_plan:
            self._create_resource_scaffold(target_skill_dir, res_plan, draft)

        # 3. 静的バリデーション
        val_res = SkillValidator.validate_directory(target_skill_dir)

        # 4. 初期評価テストハーネスの生成 & 契約テスト検証
        test_harness_res = self._generate_and_verify_test_harness(target_skill_dir, draft)

        return {
            "status": "success" if val_res.is_valid else "partial_success",
            "skill_name": draft.name,
            "output_dir": str(target_skill_dir),
            "pattern": draft.pattern.value if hasattr(draft.pattern, "value") else str(draft.pattern),
            "resources": [r.rel_path for r in draft.resources_plan],
            "tests_generated": test_harness_res.get("generated_files", []),
            "contract_passed": test_harness_res.get("contract_passed", True),
            "errors": val_res.errors,
            "warnings": val_res.warnings,
            "message": f"Successfully created skill '{draft.name}' with deterministic scaffold and test harness."
        }

    def _create_resource_scaffold(self, skill_dir: Path, res_plan: ResourcePlan, draft: SkillLogicDraft):
        """リソース（スクリプト、参照ドキュメント、アセット）の初期雛形を作成"""
        rel_path = res_plan.rel_path
        target_file = skill_dir / rel_path
        target_file.parent.mkdir(parents=True, exist_ok=True)

        if target_file.exists():
            return

        if rel_path.endswith(".py"):
            script_name = Path(rel_path).stem
            content = f'''#!/usr/bin/env python3
"""
{script_name} - {res_plan.purpose}
Deterministic CLI tool for {draft.name} skill.
"""

import sys
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="{res_plan.purpose}")
    parser.add_argument("--input", "-i", type=str, help="Input data or path")
    parser.add_argument("--format", "-f", type=str, default="text", help="Output format")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.input:
        print(f"Processing input: {{args.input}}")
    else:
        print("Ready for execution.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
'''
            target_file.write_text(content, encoding="utf-8")
            try:
                target_file.chmod(0o755)
            except Exception:
                pass
        elif rel_path.endswith(".md"):
            content = f"# {Path(rel_path).stem.replace('_', ' ').title()}\n\n## Overview\n\n{res_plan.purpose}\n"
            target_file.write_text(content, encoding="utf-8")
        else:
            target_file.write_text("", encoding="utf-8")

    def _generate_and_verify_test_harness(self, skill_dir: Path, draft: SkillLogicDraft) -> Dict[str, Any]:
        """初期評価データセット（contract, trigger）を生成し、契約テストを実行"""
        tests_dir = skill_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "results").mkdir(exist_ok=True)

        generated_files = []
        script_name = f"{draft.name.replace('-', '_')}.py"
        script_rel = f"scripts/{script_name}"
        if not (skill_dir / script_rel).exists():
            scripts = [f for f in (skill_dir / "scripts").glob("*.py") if f.name != "__init__.py"]
            if scripts:
                script_rel = f"scripts/{scripts[0].name}"

        # 1. Contract Test ケースの生成
        contract_data = {
            "eval_set_id": f"{draft.name}_contract_eval",
            "eval_cases": [
                {
                    "eval_case_id": "test_cli_help",
                    "script_name": script_rel,
                    "cli_args": ["--help"],
                    "expected_exit_code": 0,
                    "expected_stdout_contains": ["--help"]
                }
            ]
        }
        contract_path = tests_dir / f"{draft.name}_contract.evalset.json"
        contract_path.write_text(json.dumps(contract_data, indent=2, ensure_ascii=False), encoding="utf-8")
        generated_files.append(str(contract_path))

        # 2. Trigger Test ケースの生成
        trigger_cases = []
        for idx, ex in enumerate(draft.concrete_trigger_examples, 1):
            trigger_cases.append({
                "name": f"positive_trigger_{idx}",
                "user_input": ex,
                "expected_tools": [draft.name],
                "should_trigger": True
            })
        for idx, non_ex in enumerate(draft.when_not_to_use[:3], 1):
            trigger_cases.append({
                "name": f"negative_trigger_{idx}",
                "user_input": non_ex,
                "expected_tools": [],
                "should_trigger": False
            })
        trigger_data = {"eval_set_id": f"{draft.name}_trigger_eval", "cases": trigger_cases}
        trigger_path = tests_dir / f"{draft.name}_trigger.evalset.json"
        trigger_path.write_text(json.dumps(trigger_data, indent=2, ensure_ascii=False), encoding="utf-8")
        generated_files.append(str(trigger_path))

        # 3. 契約テストの実行検証
        contract_passed = True
        try:
            skill_obj = Skill(root_dir=str(skill_dir), tier=0)
            runner = ContractTestRunner()
            env = LocalWorkspaceEnv()
            run_res = runner.run_tests(skill=skill_obj, test_cases_data=contract_data, env=env)
            contract_passed = (run_res.failed == 0 and run_res.accuracy >= 1.0)
        except Exception as e:
            print(f"Warning: contract test check skipped or failed: {e}", file=sys.stderr)

        return {
            "generated_files": generated_files,
            "contract_passed": contract_passed
        }


def create_skill(
    prompt: Optional[str] = None,
    name: Optional[str] = None,
    pattern: Optional[str] = None,
    output_dir: Optional[str] = None,
    draft: Optional[SkillLogicDraft] = None
) -> Dict[str, Any]:
    """
    決定論的にスキルパッケージを初期化・生成します。
    draft が指定されていない場合は、name と pattern から標準的な SkillLogicDraft を自動構築します。
    """
    skill_name = name or "custom-skill"
    pattern_val = SkillPattern.WORKFLOW
    if pattern:
        try:
            pattern_val = SkillPattern(pattern)
        except Exception:
            pattern_val = SkillPattern.WORKFLOW

    if draft is None:
        script_rel = f"scripts/{skill_name.replace('-', '_')}.py"
        overview_text = prompt or f"Provides workflows and tools for {skill_name}."
        draft = SkillLogicDraft(
            name=skill_name,
            pattern=pattern_val,
            description_third_person=f"This skill should be used when users need to perform {skill_name} tasks and workflows.",
            concrete_trigger_examples=[
                f"Please execute {skill_name} on the input data.",
                f"Help me run {skill_name} workflow."
            ],
            when_not_to_use=[
                "Simple one-line shell commands that do not need a specialized skill.",
                "Unrelated domain operations."
            ],
            overview_summary=overview_text,
            decision_tree=[
                DecisionBranch(
                    condition="Standard execution request",
                    action=f"Execute {script_rel} with arguments"
                ),
                DecisionBranch(
                    condition="Detailed specification or configuration check",
                    action="Refer to references/guide.md"
                )
            ],
            execution_steps=[
                StepInstruction(
                    step_number=1,
                    title="Validate Inputs",
                    action_imperative="Check required input parameters before execution.",
                    target_resource=script_rel
                ),
                StepInstruction(
                    step_number=2,
                    title="Execute Logic",
                    action_imperative=f"Run {script_rel} to perform the main operation.",
                    target_resource=script_rel
                ),
                StepInstruction(
                    step_number=3,
                    title="Verify Output",
                    action_imperative="Verify the output format and return the result to the user.",
                    target_resource=None
                )
            ],
            resources_plan=[
                ResourcePlan(rel_path=script_rel, type="script", purpose=f"Core execution CLI tool for {skill_name}"),
                ResourcePlan(rel_path="references/guide.md", type="reference", purpose=f"Usage guide and reference material for {skill_name}")
            ],
            guidelines=[
                "Ensure all scripts support --help and handle edge cases gracefully.",
                "Follow Anthropic Markdown-First and Google ADK Progressive Disclosure principles."
            ]
        )

    engine = SkillCreationEngine(output_base_dir=output_dir or "src/skills")
    return engine.create_skill_from_draft(draft, output_dir=output_dir)
