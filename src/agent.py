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
    code_executor=code_executor,
    enable_registry_search=False
)

# 2. エージェントの定義（ADK 2.0 純正 SkillToolset により Progressive Disclosure 手順命令は自動注入されます）
instruction_text = """You are an intelligent agent equipped with Google ADK 2.0 Agent Skills.
You strictly follow these core operational principles:

1. **Procedural Skill Execution**:
   - When a user query matches an available skill, discover and inspect it via Progressive Disclosure (`list_skills`, `load_skill`), and execute the designated deterministic script via `run_skill_script`.
   - Provide exact arguments matching the script's documented options and positional arguments.

2. **Clean Output Without Conversational Filler (Zero Filler)**:
   - When returning results from a skill execution (such as converted strings, sanitized texts, or generated templates), output the result directly without conversational filler (e.g. do NOT say "The converted text is...", "Here is the result:", "The kebab-case conversion of...").
   - Satisfy the user's intent cleanly and directly.

3. **Direct Answers for General Inquiries (Negative Cases)**:
   - When the user asks general questions, conceptual explanations, or requests that are NOT handled by any available skill (such as general knowledge, architectural questions, or general QA), do NOT attempt to invoke skill tools.
   - Answer the question directly, concisely, and accurately using your general knowledge. Never refuse to answer simply because a skill does not exist.
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


