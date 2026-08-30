import os
import sys
import argparse
import zipfile
from pathlib import Path
from .models import SkillLogicDraft, SkillPattern, StepInstruction, ResourcePlan, DecisionBranch
from .template_engine import SkillTemplateEngine
from .validator import SkillValidator

def init_skill(skill_name: str, path: str, pattern: str = "workflow") -> Path | None:
    """新しいスキルディレクトリを Anthropic 準拠の雛形として初期化します。"""
    try:
        pat_enum = SkillPattern(pattern)
    except ValueError:
        print(f"❌ Error: Invalid pattern '{pattern}'. Choices: {[p.value for p in SkillPattern]}")
        return None

    target_dir = Path(path).resolve() / skill_name
    if target_dir.exists():
        print(f"❌ Error: Target skill directory already exists: {target_dir}")
        return None

    target_dir.mkdir(parents=True, exist_ok=False)

    script_name = f"{skill_name.replace('-', '_')}.py"

    # 雛形用ドラフトの作成
    draft = SkillLogicDraft(
        name=skill_name,
        pattern=pat_enum,
        description_third_person=f"This skill should be used when users want to perform {skill_name.replace('-', ' ')} tasks.",
        concrete_trigger_examples=[
            f"Please help me with {skill_name.replace('-', ' ')}",
            f"Execute {skill_name} on target data"
        ],
        when_not_to_use=[
            "Simple one-off commands that do not require specialized workflow execution",
            "Tasks that fall outside the domain scope or require different toolchains"
        ],
        overview_summary=f"Enables specialized execution of {skill_name.replace('-', ' ')} workflows.",
        decision_tree=[
            DecisionBranch(condition="standard request is provided", action=f"execute scripts/{script_name}")
        ],
        execution_steps=[
            StepInstruction(
                step_number=1,
                title="Initialize and Validate",
                action_imperative="Check prerequisites and input parameters before execution.",
                target_resource=f"scripts/{script_name}"
            ),
            StepInstruction(
                step_number=2,
                title="Execute Core Logic",
                action_imperative="Run the task according to specifications.",
                target_resource=f"scripts/{script_name}"
            )
        ],
        resources_plan=[
            ResourcePlan(rel_path=f"scripts/{script_name}", type="script", purpose="Core execution logic"),
            ResourcePlan(rel_path="references/guide.md", type="reference", purpose="Detailed reference documentation"),
            ResourcePlan(rel_path="assets/sample.txt", type="asset", purpose="Sample output template")
        ],
        guidelines=[
            "Always verify inputs before running scripts.",
            "Consult references/guide.md when encountered with unexpected edge cases."
        ]
    )

    # 1. SKILL.md の書き出し
    skill_md_content = SkillTemplateEngine.render(draft)
    (target_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

    scripts_dir = target_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    sample_script = scripts_dir / script_name
    title = skill_name.replace("-", " ").title()
    sample_script_code = f"""#!/usr/bin/env python3
\"\"\"
Core execution script for {skill_name}
\"\"\"

import argparse
import sys

def run(input_val: str | None = None) -> str:
    \"\"\"主要タスクを実行します。\"\"\"
    print(f"Executing {skill_name} with input: {{input_val}}")
    return "Success"

def main():
    parser = argparse.ArgumentParser(description="{title} execution script.")
    parser.add_argument("--input", "-i", type=str, help="Input argument or file path")
    args = parser.parse_args()

    run(args.input)
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
    sample_script.write_text(sample_script_code, encoding="utf-8")
    sample_script.chmod(0o755)

    references_dir = target_dir / "references"
    references_dir.mkdir(exist_ok=True)
    (references_dir / "guide.md").write_text(
        f"# Reference Guide for {skill_name}\n\nDetailed reference documentation and specifications.\n",
        encoding="utf-8"
    )

    assets_dir = target_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    (assets_dir / "sample.txt").write_text("Sample asset template\n", encoding="utf-8")

    # 3. テスト用ディレクトリ
    tests_dir = target_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "results").mkdir(exist_ok=True)

    print(f"✅ Successfully initialized skill '{skill_name}' at: {target_dir}")
    print(f"   Pattern: {pat_enum.value}")
    return target_dir


def validate_skill_cli(skill_path_str: str) -> bool:
    """スキルディレクトリの静的検証を CLI 経由で実行"""
    skill_path = Path(skill_path_str).resolve()
    print(f"🔍 Validating skill at: {skill_path} ...")
    res = SkillValidator.validate_directory(skill_path)

    if res.warnings:
        print("\n⚠️ Warnings:")
        for w in res.warnings:
            print(f"  - {w}")

    if not res.is_valid:
        print("\n❌ Validation Failed with Errors:")
        for e in res.errors:
            print(f"  - {e}")
        return False

    print("\n✅ Skill is completely valid and complies with Markdown-First / Progressive Disclosure standards!")
    return True


def package_skill_cli(skill_path_str: str, output_dir_str: str | None = None) -> Path | None:
    """スキルを検証した上で配布用 ZIP パッケージに固める"""
    skill_path = Path(skill_path_str).resolve()
    skill_name = skill_path.name

    if not validate_skill_cli(skill_path_str):
        print(f"❌ Cannot package '{skill_name}': Validation failed. Fix errors and retry.")
        return None

    out_dir = Path(output_dir_str).resolve() if output_dir_str else skill_path.parent / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{skill_name}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(skill_path):
            # tests/results などの一時ファイルは除外
            dirs[:] = [d for d in dirs if d not in ["__pycache__", "results", ".pytest_cache"]]
            for file in files:
                if file.endswith((".pyc", ".pyo")):
                    continue
                file_path = Path(root) / file
                arcname = file_path.relative_to(skill_path.parent)
                zipf.write(file_path, arcname)

    print(f"📦 Successfully packaged skill to: {zip_path}")
    return zip_path


def main():
    parser = argparse.ArgumentParser(description="edd-agent-tools Skill Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Initialize a new skill scaffold")
    p_init.add_argument("name", help="Skill name (lowercase hyphen-case)")
    p_init.add_argument("--pattern", default="workflow", choices=[p.value for p in SkillPattern], help="Skill pattern")
    p_init.add_argument("--path", default=".", help="Target parent directory")

    # validate
    p_val = subparsers.add_parser("validate", help="Validate a skill directory")
    p_val.add_argument("skill_dir", help="Path to skill directory")

    # package
    p_pkg = subparsers.add_parser("package", help="Package a skill into distributable zip")
    p_pkg.add_argument("skill_dir", help="Path to skill directory")
    p_pkg.add_argument("output_dir", nargs="?", default=None, help="Output directory for zip file")
    p_pkg.add_argument("--output", "-o", default=None, help="Output directory for zip file")

    # create (AI-driven automated generation)
    p_create = subparsers.add_parser("create", help="Generate a full skill package from natural language prompt")
    p_create.add_argument("prompt", help="Natural language requirements for the skill")
    p_create.add_argument("--name", default=None, help="Optional preferred skill name")
    p_create.add_argument("--pattern", choices=["workflow", "task_based", "reference", "capabilities"], default=None, help="Skill pattern")
    p_create.add_argument("--output", default="src/skills", help="Output directory (default: src/skills)")

    args = parser.parse_args()

    if args.command == "init":
        res = init_skill(args.name, args.path, args.pattern)
        sys.exit(0 if res else 1)
    elif args.command == "validate":
        ok = validate_skill_cli(args.skill_dir)
        sys.exit(0 if ok else 1)
    elif args.command == "package":
        out = args.output or args.output_dir
        res = package_skill_cli(args.skill_dir, out)
        sys.exit(0 if res else 1)

    elif args.command == "create":
        from .creator import create_skill
        res = create_skill(args.prompt, name=args.name, pattern=args.pattern, output_dir=args.output)
        import json
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(0 if res.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
