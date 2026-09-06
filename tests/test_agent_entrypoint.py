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
    """src.agent がエラーなくインポートでき、ADK SkillToolset、LocalSubprocessCodeExecutor、Lifecycle Callbacksがマウントされていることを検証"""
    import src.agent as agent_mod
    from edd_agent_tools.adk.executor import LocalSubprocessCodeExecutor
    from google.adk.tools.skill_toolset import SkillToolset

    agent = agent_mod.root_agent

    assert agent is not None
    assert agent.name == "evaluation_driven_development_agent"
    assert len(agent.tools) >= 1
    # SkillToolset が正しく登録されていることを検証
    assert isinstance(agent.tools[0], SkillToolset)
    assert hasattr(agent.tools[0], "get_tools")

    # ADK 2.0 BaseCodeExecutor 準拠の LocalSubprocessCodeExecutor が注入されていることを検証
    assert agent.code_executor is not None
    assert isinstance(agent.code_executor, LocalSubprocessCodeExecutor)
    assert agent.code_executor.timeout_seconds == 300

    # ADK 2.0 Workflow RetryConfig の検証
    assert agent.retry_config is not None
    assert agent.retry_config.max_attempts == 3

    # ADK 2.0 ライフサイクルコールバックの検証
    assert agent.before_agent_callback is not None
    assert agent.after_agent_callback is not None



def test_agent_app_container():
    """src.agent に Google ADK 2.0 推奨の App オブジェクトが正しく定義・エクスポートされていることを検証"""
    import src.agent as agent_mod
    from google.adk.apps import App

    assert hasattr(agent_mod, "app")
    app = agent_mod.app
    assert isinstance(app, App)
    assert app.name == "evaluation_driven_development_agent"
    assert app.root_agent == agent_mod.root_agent


def test_main_a2a_app_initialization():
    """src.main の A2A Starlette アプリケーションが正常に初期化されていることを検証"""
    import src.main as main_mod
    app = main_mod.a2a_app

    assert app is not None
    assert hasattr(app, "routes")
