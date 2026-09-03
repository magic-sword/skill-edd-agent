import os
import shutil
import pytest
from pathlib import Path
from edd_agent_tools import (
    SkillPattern,
    SkillSpec,
    SkillValidator,
    Skill,
    SkillsState,
    SkillScaffolder,
    SkillPackager
)

@pytest.fixture
def tmp_workspace(tmp_path):
    """テスト用の一時ワークスペースディレクトリ"""
    return tmp_path

def test_skill_scaffolder_and_validator(tmp_workspace):
    """SkillScaffolder による雛形生成と SkillValidator による静的検証のテスト"""
    skill_dir = SkillScaffolder.scaffold("custom-pdf-tool", output_base_dir=tmp_workspace, pattern="task_based")
    assert skill_dir is not None
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "scripts" / "custom_pdf_tool.py").exists()
    assert (skill_dir / "references" / "guide.md").exists()
    assert (skill_dir / "assets" / "sample.txt").exists()
    assert (skill_dir / "examples" / "example_usage.py").exists()

    # 静的検証
    val_res = SkillValidator.validate_directory(skill_dir)
    assert val_res.is_valid is True
    assert len(val_res.errors) == 0

    # パース検証
    content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    spec = SkillSpec.parse_markdown(content)
    assert spec.name == "custom-pdf-tool"
    assert spec.pattern == SkillPattern.TASK_BASED

def test_validator_detects_broken_resources(tmp_workspace):
    """存在しないリソースへの言及を静的リンターが検知することを確認"""
    skill_dir = SkillScaffolder.scaffold("broken-skill", output_base_dir=tmp_workspace, pattern="workflow")
    # 存在しないスクリプトへの言及を SKILL.md に追記
    skill_md = skill_dir / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    content += "\nExecute `scripts/non_existent.py` to fix issues.\n"
    skill_md.write_text(content, encoding="utf-8")

    val_res = SkillValidator.validate_directory(skill_dir)
    assert val_res.is_valid is False
    assert any("non_existent.py" in err for err in val_res.errors)

def test_skill_domain_class_resource_access(tmp_workspace):
    """Skill ドメインクラスの3層リソース解決とメタデータ取得のテスト"""
    skill_dir = SkillScaffolder.scaffold("my-domain-skill", output_base_dir=tmp_workspace, pattern="capabilities")
    skill = Skill(root_dir=str(skill_dir), tier=1)

    assert skill.name == "my-domain-skill"
    assert skill.pattern == SkillPattern.CAPABILITIES
    assert "my_domain_skill.py" in skill.list_scripts()
    assert "guide.md" in skill.list_references()
    assert "sample.txt" in skill.list_assets()
    assert "example_usage.py" in skill.list_examples()

    # リファレンスロード
    ref_content = skill.load_reference("guide.md")
    assert "Reference Guide for" in ref_content

    # 使用例ロード
    ex_content = skill.load_example("example_usage.py")
    assert "Example usage pattern for" in ex_content

    # スクリプトパス解決 & ADK 2.0 純正モデル統合テスト
    script_path = skill.get_script_path("my_domain_skill.py")
    assert script_path.endswith("my_domain_skill.py")
    
    # ADK 2.0 純正 Skill オブジェクトの検証
    adk_skill = skill.adk_skill
    assert adk_skill is not None
    assert adk_skill.frontmatter.name == "my-domain-skill"
    assert "my_domain_skill.py" in adk_skill.resources.scripts

def test_cli_package(tmp_workspace):
    """SkillPackager によるパッケージング機能のテスト"""
    skill_dir = SkillScaffolder.scaffold("pkg-test-skill", output_base_dir=tmp_workspace, pattern="workflow")
    dist_dir = tmp_workspace / "dist"
    zip_path = SkillPackager.package(skill_dir=skill_dir, output_dir=dist_dir, validate=True)
    assert zip_path is not None
    assert zip_path.exists()

def test_skill_evolver_integration():
    """自己改善メタスキル skill-evolver の静的検証と状態管理のテスト"""
    evolver_dir = Path("/workspace/src/skills/skill-evolver")
    val_res = SkillValidator.validate_directory(evolver_dir)
    assert val_res.is_valid is True, f"Validation errors: {val_res.errors}"

    state = SkillsState()
    evolver_skill = state.get_skill("skill-evolver")
    assert evolver_skill is not None
    assert (Path(evolver_skill.root_dir) / "SKILL.md").exists()


def test_validator_prerequisites_detection(tmp_workspace):
    """外部ライブラリを import するスクリプトに対し SKILL.md の Requirements 記載を検証するテスト"""
    skill_dir = SkillScaffolder.scaffold("docx-parser-skill", output_base_dir=tmp_workspace, pattern="task_based")

    # 外部パッケージ (docx) を import するスクリプトを配置
    script_path = skill_dir / "scripts" / "docx_parser_skill.py"
    script_path.write_text("""#!/usr/bin/env python3
import sys
import argparse
import docx

def main():
    pass

if __name__ == '__main__':
    main()
""", encoding="utf-8")

    # 1. Requirements 記載がない場合 -> 警告が出る
    val_res = SkillValidator.validate_directory(skill_dir)
    assert any("docx" in w and "Requirements & Prerequisites" in w for w in val_res.warnings)

    # 2. SKILL.md に Requirements & Prerequisites を追記した場合 -> 警告が解消する
    skill_md = skill_dir / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    content += "\n## Requirements & Prerequisites\n- `pip install python-docx`\n- `docx` library\n"
    skill_md.write_text(content, encoding="utf-8")

    val_res2 = SkillValidator.validate_directory(skill_dir)
    assert not any("docx" in w and "Requirements & Prerequisites" in w for w in val_res2.warnings)


def test_validator_adk_spec_enforcement(tmp_workspace):
    """ADK 2.0 / AgentSkills 仕様（文字数制約・ハイフン制約）のバリデータ検査をテスト"""
    # 1. 64文字超過スキル名
    long_name = "a" * 65
    invalid_content = f"---\nname: {long_name}\ndescription: Valid description\n---\n# Test"
    res = SkillValidator.validate_content(invalid_content)
    assert not res.is_valid
    assert any("64 characters" in e for e in res.errors)

    # 2. 連続ハイフン
    double_hyphen_content = "---\nname: my--skill\ndescription: Valid description\n---\n# Test"
    res2 = SkillValidator.validate_content(double_hyphen_content)
    assert not res2.is_valid
    assert any("consecutive hyphens" in e for e in res2.errors)

    # 3. 1024文字超過 description
    long_desc = "x" * 1025
    long_desc_content = f"---\nname: valid-name\ndescription: \"{long_desc}\"\n---\n# Test"
    res3 = SkillValidator.validate_content(long_desc_content)
    assert not res3.is_valid
    assert any("1024 characters" in e for e in res3.errors)

def test_cli_contract_runner(tmp_workspace):
    """ContractTestRunner による CLI サブプロセス実行テストを検証"""
    from edd_agent_tools.evaluation import ContractTestRunner, LocalWorkspaceEnv
    from edd_agent_tools.models import EvalCaseSet, EvalCase

    skill_dir = SkillScaffolder.scaffold("cli-contract-skill", output_base_dir=tmp_workspace, pattern="workflow")
    skill = Skill(root_dir=str(skill_dir), tier=1)

    eval_set = EvalCaseSet(
        eval_set_id="cli_test_set",
        eval_cases=[
            EvalCase(
                eval_case_id="cli_normal",
                script_name="scripts/cli_contract_skill.py",
                cli_args=["--input", "hello_world"],
                expected_exit_code=0,
                expected_stdout_contains=["Executing cli-contract-skill", "hello_world"]
            ),
            EvalCase(
                eval_case_id="cli_help",
                script_name="scripts/cli_contract_skill.py",
                cli_args=["--help"],
                expected_exit_code=0,
                expected_stdout_contains=["--input"]
            )
        ]
    )

    runner = ContractTestRunner()
    env = LocalWorkspaceEnv(workspace_dir=str(tmp_workspace))
    res = runner.run_tests(skill=skill, test_cases_data=eval_set, env=env)

    assert res.passed == 2
    assert res.failed == 0
    assert res.accuracy == 1.0


def test_validator_context_rot_and_debt_detection():
    """Context Rot (>5,000 words) および Context Debt (ALWAYS/NEVER 乱用) の静的検知テスト"""
    # 1. 大文字命令の乱用 (Context Debt)
    debt_content = """---
name: debt-skill
description: Performs tasks. Use when the user asks for it.
---
# Debt Skill
ALWAYS do A. NEVER do B. MUST NOT do C. ALWAYS do D. NEVER do E.
"""
    res_debt = SkillValidator.validate_content(debt_content)
    assert any("context_debt" in issue.category for issue in res_debt.issues)

    # 2. 巨大な本文 (Context Rot)
    large_body = "word " * 5001
    rot_content = f"""---
name: rot-skill
description: Performs tasks. Use when the user asks for it.
---
# Rot Skill
{large_body}
"""
    res_rot = SkillValidator.validate_content(rot_content)
    assert any("context_rot" in issue.category for issue in res_rot.issues)


def test_simulation_runner_edd_composite_eval(tmp_workspace):
    """白書 Snippet 3 準拠の EDD 複合ケース（Trigger, Trajectory, Rubric）の評価テスト"""
    from edd_agent_tools.evaluation import SimulationEvalRunner
    skill_dir = SkillScaffolder.scaffold("edd-eval-skill", output_base_dir=tmp_workspace, pattern="workflow")
    skill = Skill(root_dir=str(skill_dir), tier=1)

    edd_eval_data = {
        "eval_set_id": "edd_composite_test",
        "cases": [
            {
                "case_id": "edd_001",
                "input": "Execute edd-eval-skill workflow",
                "expected_skill": "edd-eval-skill",
                "expected_tool_calls": [
                    {"tool": "scripts/edd_eval_skill.py", "args": {"--help": True}}
                ],
                "expected_output_format": "success",
                "rubric": ["correct execution", "clear response"]
            }
        ]
    }

    runner = SimulationEvalRunner()
    result = runner.run_tests(skill=skill, eval_set_data=edd_eval_data)
    assert result.passed == 1
    assert result.failed == 0
    assert result.accuracy == 1.0


def test_ssot_all_production_skills_contract_and_eval():
    """本番スキル（case-converter, secret-sanitizer）の *.test.json（SSOT）から直接契約テスト・EDD評価が100%パスすることを検証"""
    import json
    from edd_agent_tools.evaluation import ContractTestRunner, SimulationEvalRunner, LocalWorkspaceEnv

    skills_root = Path("/workspace/src/skills")
    target_skills = ["case-converter", "secret-sanitizer"]

    contract_runner = ContractTestRunner()
    sim_runner = SimulationEvalRunner()
    env = LocalWorkspaceEnv(workspace_dir="/workspace")

    for s_name in target_skills:
        s_dir = skills_root / s_name
        skill = Skill(root_dir=str(s_dir), tier=1)

        evalset_file = s_dir / "tests" / f"{s_name}.test.json"
        assert evalset_file.exists(), f"SSOT evalset not found at: {evalset_file}"

        data = json.loads(evalset_file.read_text(encoding="utf-8"))

        # 1. Contract Test (CLI Black-box 実行)
        res_contract = contract_runner.run_tests(skill=skill, test_cases_data=data, env=env)
        assert res_contract.failed == 0, f"Contract tests failed for {s_name}: {res_contract.failed_cases}"
        assert res_contract.passed > 0, f"No contract cases executed for {s_name}"

        # 2. EDD Composite Test (Trigger, Trajectory, Rubric)
        res_sim = sim_runner.run_tests(skill=skill, eval_set_data=data, env=env)
        assert res_sim.failed == 0, f"EDD composite eval failed for {s_name}: {res_sim.failed_cases}"
        assert res_sim.accuracy == 1.0, f"EDD accuracy < 1.0 for {s_name}: {res_sim.accuracy}"

