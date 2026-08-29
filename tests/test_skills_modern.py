import os
import shutil
import pytest
from pathlib import Path
from edd_agent_tools.skills import (
    SkillPattern,
    SkillLogicDraft,
    SkillSpec,
    SkillTemplateEngine,
    SkillValidator,
    Skill,
    SkillsState
)
from edd_agent_tools.skills.models import DecisionBranch, StepInstruction, ResourcePlan
from edd_agent_tools.skills.cli import init_skill, validate_skill_cli, package_skill_cli

@pytest.fixture
def tmp_workspace(tmp_path):
    """テスト用の一時ワークスペースディレクトリ"""
    return tmp_path

def test_skill_logic_draft_and_template_engine():
    """SkillLogicDraft から SkillTemplateEngine による SKILL.md レンダリングの検証"""
    draft = SkillLogicDraft(
        name="test-converter",
        pattern=SkillPattern.WORKFLOW,
        description_third_person="This skill should be used when users need to convert markdown files to HTML.",
        concrete_trigger_examples=[
            "Convert report.md to HTML",
            "Please build html from markdown"
        ],
        overview_summary="Converts Markdown documents into HTML format using custom styles.",
        decision_tree=[
            DecisionBranch(condition="input is raw markdown", action="execute scripts/convert.py"),
            DecisionBranch(condition="custom CSS is needed", action="reference references/styles.md")
        ],
        execution_steps=[
            StepInstruction(
                step_number=1,
                title="Verify Input File",
                action_imperative="Check if the target markdown file exists and is readable.",
                target_resource="scripts/convert.py"
            ),
            StepInstruction(
                step_number=2,
                title="Execute Conversion",
                action_imperative="Run scripts/convert.py with input and output paths.",
                target_resource="scripts/convert.py"
            )
        ],
        resources_plan=[
            ResourcePlan(rel_path="scripts/convert.py", type="script", purpose="Core markdown parser and HTML builder"),
            ResourcePlan(rel_path="references/styles.md", type="reference", purpose="Style guidelines and class names"),
            ResourcePlan(rel_path="assets/template.html", type="asset", purpose="Base HTML skeleton")
        ],
        guidelines=[
            "Always validate HTML output after conversion."
        ]
    )

    rendered_md = SkillTemplateEngine.render(draft)
    assert "name: test-converter" in rendered_md
    assert "description: This skill should be used when" in rendered_md
    assert "# Test Converter" in rendered_md
    assert "## Workflow Decision Tree" in rendered_md
    assert "## Step-by-Step Instructions" in rendered_md
    assert "### `scripts/` (Executable Tools)" in rendered_md
    assert "### `references/` (On-Demand Knowledge)" in rendered_md
    assert "### `assets/` (Output Templates & Boilerplates)" in rendered_md

    # パース検証
    spec = SkillSpec.parse_markdown(rendered_md)
    assert spec.name == "test-converter"
    assert spec.pattern == SkillPattern.WORKFLOW
    assert "convert.py" in spec.scripts[0]
    assert "styles.md" in spec.references[0]
    assert "template.html" in spec.assets[0]

def test_skill_init_and_validator(tmp_workspace):
    """init_skill による雛形生成と SkillValidator による静的検証のテスト"""
    skill_dir = init_skill("custom-pdf-tool", path=str(tmp_workspace), pattern="task_based")
    assert skill_dir is not None
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "scripts" / "main.py").exists()
    assert (skill_dir / "references" / "guide.md").exists()
    assert (skill_dir / "assets" / "sample.txt").exists()

    # 静的検証
    val_res = SkillValidator.validate_directory(skill_dir)
    assert val_res.is_valid is True
    assert len(val_res.errors) == 0

def test_validator_detects_broken_resources(tmp_workspace):
    """存在しないリソースへの言及を静的リンターが検知することを確認"""
    skill_dir = init_skill("broken-skill", path=str(tmp_workspace), pattern="workflow")
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
    skill_dir = init_skill("my-domain-skill", path=str(tmp_workspace), pattern="capabilities")
    skill = Skill(root_dir=str(skill_dir), tier=1)

    assert skill.name == "my-domain-skill"
    assert skill.pattern == SkillPattern.CAPABILITIES
    assert "main.py" in skill.list_scripts()
    assert "guide.md" in skill.list_references()
    assert "sample.txt" in skill.list_assets()

    # リファレンスロード
    ref_content = skill.load_reference("guide.md")
    assert "Reference Guide for my-domain-skill" in ref_content

    # ツール取得テスト
    tools = skill.get_tools()
    assert len(tools) >= 1
    tool = skill.get_tool()
    assert tool.name == "run"
    assert tool.func() == "Success"

def test_cli_package(tmp_workspace):
    """CLI package 機能のテスト"""
    skill_dir = init_skill("pkg-test-skill", path=str(tmp_workspace), pattern="workflow")
    dist_dir = tmp_workspace / "dist"
    zip_path = package_skill_cli(str(skill_dir), output_dir_str=str(dist_dir))
    assert zip_path is not None
    assert zip_path.exists()
