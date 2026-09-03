"""
Google ADK 2.0 および Anthropic 標準に完全準拠した統合エージェント・エントリーポイント。
SkillToolset による Progressive Disclosure（段階的情報開示）アーキテクチャを実現。
"""

import os
import sys
from pathlib import Path

# Google ADK 2.0 互換性保証: GEMINI_API_KEY と GOOGLE_API_KEY の相互同期
if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
elif os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

from google.adk import Agent
from google.adk.code_executors import UnsafeLocalCodeExecutor
from google.adk.workflow import RetryConfig
from edd_agent_tools.adk import create_adk_skill_toolset


# 1. 登録スキルと Tier 状態に基づき ADK 公式の SkillToolset を構築
# Tier 1 以上のスキル（および必須システムスキル）を登録し、ADK 2.0 公式 Progressive Disclosure を実現
# （L1 Frontmatter は list_skills で提示され、L2 手順書や L3 スクリプトはオンデマンドで開示・実行）
# ADK 公式の UnsafeLocalCodeExecutor を標準注入し、決定論的スクリプト実行を委譲
skills_dir = Path(__file__).parent / "skills"
code_executor = UnsafeLocalCodeExecutor()
skill_toolset = create_adk_skill_toolset(
    skills_dir=skills_dir,
    min_tier=1,
    include_system_skills={"skill-creator", "skill-evolver", "creating-skills", "evolving-skills"},
    code_executor=code_executor
)

# 2. エージェントの定義（ADK 2.0 純正 SkillToolset により Progressive Disclosure 命令は自動注入）
instruction_text = """あなたは評価駆動開発（EDD: Evaluation-Driven Development）およびスキルの自己進化を自律遂行する統合エージェントです。
Google ADK 2.0 および Anthropic 公式標準（Markdown-First & Progressive Disclosure）に従って動作します。

## 主要責務と行動指針
1. **スキルの活用と探索**: マウントされた SkillToolset を通じて、必要に応じてスキル（Level 2 手順書）やリソース（Level 3 スクリプト/リファレンス）をオンデマンドで活用してタスクを解決してください。
2. **自己進化と品質保証**: 新規スキルの設計・作成は `skill-creator` を、スキルのテスト評価・失敗診断・自己修復・Tier昇格は `skill-evolver` を自律的に実行して達成してください。
3. **安全な実行環境**: 決定論的スクリプトはコンテキストを節約するためブラックボックス実行（run_skill_script）してください。
"""

# ADK 2.0 Workflow Runtime 推奨の自動リトライ設定
retry_config = RetryConfig(max_attempts=3)

root_agent = Agent(
    model='gemini-2.5-flash',
    name='evaluation_driven_development_agent',
    description='Google ADK 2.0 と Anthropic スキル標準に完全準拠した自己進化型評価駆動開発エージェント',
    instruction=instruction_text,
    retry_config=retry_config,
    tools=[
        skill_toolset
    ]
)


