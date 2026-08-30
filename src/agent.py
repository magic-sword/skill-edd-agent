"""
Google ADK 2.0 および Anthropic 標準に完全準拠した統合エージェント・エントリーポイント。
SkillToolset による Progressive Disclosure（段階的情報開示）アーキテクチャを実現。
"""

import sys
from pathlib import Path
from google.adk import Agent
from google.adk.tools.environment import EnvironmentToolset
from google.adk.environment import LocalEnvironment
from edd_agent_tools.adk import create_adk_skill_toolset

# 1. 登録スキルと Tier 状態に基づき ADK 公式の SkillToolset を構築
skills_dir = Path(__file__).parent / "skills"
skill_toolset = create_adk_skill_toolset(
    skills_dir=skills_dir,
    min_tier=1,
    include_system_skills={"skill-creator", "skill-evolver"}
)

# 2. エージェントの定義（FunctionTool の一括展開を排除し、コンテキスト消費を極小化）
instruction_text = """あなたは評価駆動開発（EDD）および自己進化型スキル開発を自律遂行する統合エージェントです。
Google ADK 2.0 および Anthropic 公式標準の Progressive Disclosure（段階的情報開示）と Markdown-First 原則に従って動作してください。

## 動作原則 (Progressive Disclosure)
1. 提供されている `SkillToolset` のツール群を用いてスキルを管理・実行する：
   - `list_skills`: 利用可能なスキル一覧（名前と説明）を確認する（Level 1）
   - `load_skill`: 選択したスキルの `SKILL.md`（手順・意思決定ツリー）をオンデマンドでロードする（Level 2）
   - `load_skill_resource`: `references/` や `assets/` のファイルを必要に応じて取得する（Level 3）
   - `run_skill_script`: `scripts/` 配下の Python/Bash スクリプトをブラックボックス実行する（Level 3）
2. 開発環境の操作や追加のシェルコマンド実行には `EnvironmentToolset`（LocalEnvironment）を利用する。
3. テスト・評価・自己修復ループは `skill-evolver` を通じて自律的に実行する。
"""

root_agent = Agent(
    model='gemini-2.5-flash',
    name='evaluation_driven_development_agent',
    description='Google ADK と Anthropic スキル標準に完全準拠した、自己進化型評価駆動開発エージェント',
    instruction=instruction_text,
    tools=[
        skill_toolset,
        EnvironmentToolset(environment=LocalEnvironment())
    ]
)
