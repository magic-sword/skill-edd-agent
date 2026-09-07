"""
Tests for Workspace / Layered Linking (Transparent Multi-Repo Integration)
"""

import os
import json
import subprocess
import pytest
from pathlib import Path

from edd_agent_tools.core.workspace_link import WorkspaceLinkManager, WorkspaceLinkConfig
from edd_agent_tools.state import SkillsState
from edd_agent_tools import cli


def test_workspace_link_manager_link_and_unlink(tmp_path: Path):
    """上流リポジトリのリンクと解除、および .gitignore への自動登録を検証。"""
    # 擬似的な上流リポジトリを作成
    upstream_dir = tmp_path / "upstream_repo"
    upstream_skills = upstream_dir / "src" / "skills"
    test_skill_dir = upstream_skills / "upstream-sample"
    test_skill_dir.mkdir(parents=True)
    (test_skill_dir / "SKILL.md").write_text(
        "---\nname: upstream-sample\ndescription: Sample upstream skill\n---\n# Upstream Sample\n",
        encoding="utf-8"
    )

    # 擬似的なローカルプロジェクトを作成
    local_dir = tmp_path / "local_repo"
    local_dir.mkdir()
    (local_dir / ".gitignore").write_text("node_modules/\n.venv/\n", encoding="utf-8")

    mgr = WorkspaceLinkManager(workspace_root=local_dir)
    res = mgr.link(upstream_dir)

    assert res["status"] == "success"
    assert res["upstream_path"] == str(upstream_dir.resolve())
    assert res["skills_count"] == 1
    assert "upstream-sample" in res["detected_skills"]
    assert res["gitignore_updated"] is True

    # .gitignore に .edd.json が含まれていることを確認
    gitignore_content = (local_dir / ".gitignore").read_text(encoding="utf-8")
    assert ".edd.json" in gitignore_content

    # .edd.json の内容確認
    cfg = mgr.get_link_config()
    assert cfg is not None
    assert cfg.upstream_path == str(upstream_dir.resolve())
    assert cfg.upstream_skills_dir == str(upstream_skills.resolve())

    # 解除テスト
    assert mgr.unlink() is True
    assert not (local_dir / ".edd.json").exists()
    assert mgr.get_link_config() is None


def test_skills_state_layered_discovery_with_link(tmp_path: Path):
    """SkillsState が .edd.json のリンク設定を通じて上流スキルを自動検出し、実体パスを保持することを検証。"""
    # 上流リポジトリ
    upstream_dir = tmp_path / "skill-edd-agent"
    upstream_skills = upstream_dir / "src" / "skills" / "shared-calculator"
    upstream_skills.mkdir(parents=True)
    (upstream_skills / "SKILL.md").write_text(
        "---\nname: shared-calculator\ndescription: Calculates expressions\n---\n# Calculator\n",
        encoding="utf-8"
    )
    # 上流の skills_state.json で Tier 2 を設定
    (upstream_dir / "skills_state.json").write_text(
        json.dumps({
            "entries": [{"path": "src/skills"}],
            "inherits": [],
            "exclude": [],
            "skills": {"shared-calculator": {"tier": 2}},
            "agents": {}
        }),
        encoding="utf-8"
    )

    # ローカルプロジェクト
    local_dir = tmp_path / "my_biz_app"
    local_skills = local_dir / "skills" / "local-helper"
    local_skills.mkdir(parents=True)
    (local_skills / "SKILL.md").write_text(
        "---\nname: local-helper\ndescription: Local helper tool\n---\n# Helper\n",
        encoding="utf-8"
    )

    # リンク設定
    mgr = WorkspaceLinkManager(workspace_root=local_dir)
    mgr.link(upstream_dir)

    # ローカルプロジェクト側で SkillsState を初期化
    state = SkillsState(project_root=local_dir)
    discovered = state.scan_skills()

    # ローカルスキルと上流スキルの両方が検出されていること
    assert "local-helper" in discovered
    assert "shared-calculator" in discovered

    # 実体パス（物理パス）が正しく分離されていること
    assert str(discovered["local-helper"].root_dir).startswith(str(local_dir))
    assert str(discovered["shared-calculator"].root_dir).startswith(str(upstream_dir))

    # 上流の Tier 2 がフォールバック継承されていること
    assert discovered["shared-calculator"].tier == 2


def test_git_isolation_and_upstream_tracking(tmp_path: Path):
    """上流スキルを変更した際、ローカルのGit差分はゼロのままで、上流リポジトリにのみ差分が現れることを検証。"""
    # 上流リポジトリ（Git 初期化）
    upstream_dir = tmp_path / "upstream_git_repo"
    upstream_dir.mkdir()
    subprocess.run(["git", "init"], cwd=str(upstream_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "TestUser"], cwd=str(upstream_dir), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(upstream_dir), check=True)

    up_skill = upstream_dir / "src" / "skills" / "convert-tool"
    up_skill.mkdir(parents=True)
    (up_skill / "SKILL.md").write_text("---\nname: convert-tool\ndescription: V1\n---\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(upstream_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial upstream commit"], cwd=str(upstream_dir), check=True, capture_output=True)

    # ローカルリポジトリ（Git 初期化）
    local_dir = tmp_path / "local_git_repo"
    local_dir.mkdir()
    subprocess.run(["git", "init"], cwd=str(local_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "TestUser"], cwd=str(local_dir), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(local_dir), check=True)
    (local_dir / "app.py").write_text("print('App V1')\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(local_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial local commit"], cwd=str(local_dir), check=True, capture_output=True)

    # 1. リンク実行
    mgr = WorkspaceLinkManager(workspace_root=local_dir)
    mgr.link(upstream_dir)

    # .gitignore をローカルでコミット
    subprocess.run(["git", "add", ".gitignore"], cwd=str(local_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add .gitignore"], cwd=str(local_dir), check=True, capture_output=True)

    # リンク直後: 両リポジトリとも clean であること
    st_loc = subprocess.run(["git", "status", "--porcelain"], cwd=str(local_dir), capture_output=True, text=True)
    st_up = subprocess.run(["git", "status", "--porcelain"], cwd=str(upstream_dir), capture_output=True, text=True)
    assert st_loc.stdout.strip() == ""
    assert st_up.stdout.strip() == ""

    # 2. 自律改善ループを模倣: エージェントが上流スキルのファイルを現場で改善・修正
    state = SkillsState(project_root=local_dir)
    skill_obj = state.get_skill("convert-tool")
    assert skill_obj is not None
    # 実体ファイルを更新
    target_skill_md = Path(skill_obj.root_dir) / "SKILL.md"
    target_skill_md.write_text("---\nname: convert-tool\ndescription: V2 Improved from field test\n---\n", encoding="utf-8")

    # 3. 差分の分離検証！
    # ★ローカルプロジェクトの Git 差分は完全にゼロ（クリーン）！
    st_loc_after = subprocess.run(["git", "status", "--porcelain"], cwd=str(local_dir), capture_output=True, text=True)
    assert st_loc_after.stdout.strip() == "", "ローカルプロジェクトに差分が出てはなりません！"

    # ★上流リポジトリの Git にのみ修正差分が現れること！
    st_up_after = subprocess.run(["git", "status", "--porcelain"], cwd=str(upstream_dir), capture_output=True, text=True)
    assert "M src/skills/convert-tool/SKILL.md" in st_up_after.stdout

    # 4. WorkspaceLinkManager の Git ヘルパー検証
    up_status = mgr.get_upstream_git_status()
    assert up_status["status"] == "success"
    assert up_status["has_changes"] is True
    assert any("convert-tool/SKILL.md" in f for f in up_status["changed_files"])

    diff_text = mgr.get_upstream_git_diff()
    assert "+description: V2 Improved from field test" in diff_text


def test_cli_link_and_status(tmp_path: Path, monkeypatch, capsys):
    """CLI edd link, edd status, edd upstream status の結合動作検証。"""
    upstream_dir = tmp_path / "upstream_cli_repo"
    up_skills = upstream_dir / "src" / "skills" / "cli-tool"
    up_skills.mkdir(parents=True)
    (up_skills / "SKILL.md").write_text("---\nname: cli-tool\ndescription: CLI test\n---\n", encoding="utf-8")

    local_dir = tmp_path / "local_cli_app"
    local_dir.mkdir()

    # カレントディレクトリをローカルプロジェクトに切り替え
    monkeypatch.chdir(local_dir)

    # 1. edd link
    ret_link = cli.main(["link", str(upstream_dir)])
    assert ret_link == 0
    out_link = capsys.readouterr().out
    assert "上流リポジトリをリンクしました" in out_link
    assert "cli-tool" in out_link

    # 2. edd status
    ret_stat = cli.main(["status"])
    assert ret_stat == 0
    out_stat = capsys.readouterr().out
    assert "Upstream Repo" in out_stat
    assert "cli-tool" in out_stat
    assert "[Upstream]" in out_stat

    # 3. edd unlink
    ret_unlink = cli.main(["unlink"])
    assert ret_unlink == 0
    out_unlink = capsys.readouterr().out
    assert "リンク設定 (.edd.json) を解除しました" in out_unlink
