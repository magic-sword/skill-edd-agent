import os
import shutil
import pytest
from pathlib import Path
from edd_agent_tools.skills import Skill, SkillValidator

@pytest.fixture
def temp_output_dir(tmp_path):
    out_dir = tmp_path / "skills_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def test_skill_creator_end_to_end(temp_output_dir):
    """skill-creator によるエンドツーエンドのスキル自動生成テスト"""
    # 1. skill-creator を Skill クラス経由でロード
    creator_skill = Skill(root_dir="/workspace/src/skills/skill-creator")
    creator_mod = creator_skill.load_module("creator.py")
    assert hasattr(creator_mod, "create_skill")

    prompt = """
    ユーザーから提供されたテキストファイルの行数、単語数、文字数を解析し、集計レポートを出力する text-analyzer スキルを作成してください。
    実行スクリプトとして analyze.py を含め、簡単な使用ガイドラインを references/ に配置してください。
    """
    
    # 2. create_skill の実行
    result = creator_mod.create_skill(
        prompt=prompt,
        name="text-analyzer",
        pattern="workflow",
        output_dir=str(temp_output_dir)
    )

    assert result["status"] == "success"
    target_dir = Path(result["output_dir"])
    assert target_dir.exists()
    assert (target_dir / "SKILL.md").exists()

    # 3. 静的バリデーションの検証
    val_res = SkillValidator.validate_directory(target_dir)
    assert val_res.is_valid is True
    assert len(val_res.errors) == 0

    # 4. 生成されたスキルを Skill ドメインクラスでロード
    generated_skill = Skill(root_dir=str(target_dir), tier=1)
    assert generated_skill.name == "text-analyzer"
    assert len(generated_skill.list_scripts()) >= 1
