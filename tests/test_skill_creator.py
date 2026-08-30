import os
import shutil
import pytest
import subprocess
import sys
from pathlib import Path
from edd_agent_tools import Skill, SkillValidator, SkillCreationEngine
from edd_agent_tools.skills.creator import create_skill


@pytest.fixture
def temp_output_dir(tmp_path):
    out_dir = tmp_path / "skills_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def test_package_level_skill_creator_engine(temp_output_dir):
    """edd-agent-tools パッケージ側の SkillCreationEngine による自動スキル生成テスト"""
    prompt = """
    ユーザーから提供されたテキストファイルの行数、単語数、文字数を解析し、集計レポートを出力する text-analyzer スキルを作成してください。
    実行スクリプトとして analyze.py を含め、簡単な使用ガイドラインを references/ に配置してください。
    """
    
    result = create_skill(
        prompt=prompt,
        name="text-analyzer",
        pattern="workflow",
        output_dir=str(temp_output_dir)
    )

    assert result["status"] == "success"
    target_dir = Path(result["output_dir"])
    assert target_dir.exists()
    assert (target_dir / "SKILL.md").exists()

    # 静的バリデーションの検証
    val_res = SkillValidator.validate_directory(target_dir)
    assert val_res.is_valid is True
    assert len(val_res.errors) == 0

    # 生成されたスキルを Skill ドメインクラスでロード
    generated_skill = Skill(root_dir=str(target_dir), tier=1)
    assert generated_skill.name == "text-analyzer"
    assert len(generated_skill.list_scripts()) >= 1


def test_skill_creator_zero_dependency_scripts(tmp_path):
    """src/skills/skill-creator 配下の Zero-dependency スクリプト（init, validate, package）の動作テスト"""
    creator_dir = Path("/workspace/src/skills/skill-creator")
    init_script = creator_dir / "scripts" / "init_skill.py"
    val_script = creator_dir / "scripts" / "quick_validate.py"
    pkg_script = creator_dir / "scripts" / "package_skill.py"

    assert init_script.exists()
    assert val_script.exists()
    assert pkg_script.exists()

    # 1. init_skill.py で新規スキル雛形を生成
    out_dir = tmp_path / "zero_dep_skills"
    res_init = subprocess.run(
        [sys.executable, str(init_script), "demo-converter", "--path", str(out_dir), "--pattern", "workflow"],
        capture_output=True,
        text=True
    )
    assert res_init.returncode == 0
    demo_dir = out_dir / "demo-converter"
    assert demo_dir.exists()
    assert (demo_dir / "SKILL.md").exists()

    # 2. quick_validate.py で検証
    res_val = subprocess.run(
        [sys.executable, str(val_script), str(demo_dir)],
        capture_output=True,
        text=True
    )
    assert res_val.returncode == 0
    assert "is valid" in res_val.stdout

    # 3. package_skill.py で ZIP 出力
    dist_dir = tmp_path / "dist"
    res_pkg = subprocess.run(
        [sys.executable, str(pkg_script), str(demo_dir), "--output", str(dist_dir)],
        capture_output=True,
        text=True
    )
    assert res_pkg.returncode == 0
    assert (dist_dir / "demo-converter.zip").exists()
