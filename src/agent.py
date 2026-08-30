"""
Google ADK 2.0 および Anthropic 標準に完全準拠した統合エージェント・エントリーポイント。
SkillToolset による Progressive Disclosure（段階的情報開示）アーキテクチャを実現。
"""

import sys
from pathlib import Path
from google.adk import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.tools.environment import EnvironmentToolset
from google.adk.environment import LocalEnvironment
from edd_agent_tools.skills import SkillsState, SkillTier

# 1. 全ての登録スキルのメタデータを解決
state = SkillsState()
skills_dir = Path("/workspace/src/skills")
system_skills = {
    "skill-creator", "skill-evaluator", "skill-diagnoser",
    "skill-optimizer", "skill-planner"
}

# 2. ADK ネイティブの Skill モデルとしてロード（Tier 0 SANDBOX は除外し、システムスキルは常に含める）
loaded_adk_skills = []
for skill_meta in state.list_skills():
    if skill_meta.tier == SkillTier.SANDBOX and skill_meta.name not in system_skills:
        continue
    skill_path = skills_dir / skill_meta.name
    if skill_path.exists() and (skill_path / "SKILL.md").exists():
        try:
            adk_skill = load_skill_from_dir(skill_path)
            loaded_adk_skills.append(adk_skill)
        except Exception as e:
            print(f"Warning: {skill_meta.name} の ADK スキルロードに失敗しました: {e}", file=sys.stderr)

# 3. ADK 標準の SkillToolset を構築（list_skills, load_skill, load_skill_resource, run_skill_script を自動管理）
skill_toolset = SkillToolset(skills=loaded_adk_skills)

# 4. エージェントの定義（FunctionTool の一括展開を排除し、コンテキスト消費を極小化）
instruction_text = """あなたは評価駆動開発（EDD）および自己進化型スキル開発を自律遂行する統合エージェントです。
Google ADK 2.0 および Anthropic 公式標準の Progressive Disclosure（段階的情報開示）と Markdown-First 原則に従って動作してください。

## 動作原則 (Progressive Disclosure)
1. 提供されている `SkillToolset` のツール群を用いてスキルを管理・実行する：
   - `list_skills`: 利用可能なスキル一覧（名前と説明）を確認する（Level 1）
   - `load_skill`: 選択したスキルの `SKILL.md`（手順・意思決定ツリー）をオンデマンドでロードする（Level 2）
   - `load_skill_resource`: `references/` や `assets/` のファイルを必要に応じて取得する（Level 3）
   - `run_skill_script`: `scripts/` 配下の Python/Bash スクリプトをブラックボックス実行する（Level 3）
2. 開発環境の操作や追加のシェルコマンド実行には `EnvironmentToolset`（LocalEnvironment）を利用する。
3. テスト・評価・自己修復ループは `skill-evaluator` および `skill-optimizer` を通じて自律的に実行する。
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
