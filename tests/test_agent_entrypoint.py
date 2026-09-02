"""
test_agent_entrypoint.py - Google ADK 2.0 & A2A エージェント統合テスト
"""

import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
workspace_dir = str(Path(__file__).parent.parent)
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

import pytest


def test_agent_initialization_and_skill_toolset():
    """src.agent がエラーなくインポートでき、ADK SkillToolset がマウントされていることを検証"""
    import src.agent as agent_mod
    agent = agent_mod.root_agent

    assert agent is not None
    assert agent.name == "evaluation_driven_development_agent"
    assert len(agent.tools) >= 1
    # SkillToolset が正しく登録されていることを検証
    assert hasattr(agent.tools[0], "get_tools") or hasattr(agent.tools[0], "skills_dir")



def test_main_a2a_app_initialization():
    """src.main の A2A Starlette アプリケーションが正常に初期化されていることを検証"""
    import src.main as main_mod
    app = main_mod.a2a_app

    assert app is not None
    assert hasattr(app, "routes")
