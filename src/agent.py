"""
A2Aプロトコル互換のエージェント・エントリーポイント。
Anthropic 公式標準の Markdown-First & Progressive Disclosure アーキテクチャに準拠した統合エージェント。
"""

import sys
from google.adk import Agent
from google.adk.tools.environment import EnvironmentToolset
from google.adk.environment import LocalEnvironment
from edd_agent_tools.skills import SkillsState, SkillTier

# 全ての登録スキルおよびワークフローエージェントを解決
state = SkillsState()
skills = state.list_skills()

# システムコア・メタスキルの定義
system_skills = {
    "skill-creator", "skill-evaluator", "skill-diagnoser", 
    "skill-optimizer", "skill-planner"
}

# 登録スキルをツールとしてロード（Tier 0 SANDBOX は除外し、システムスキルは常に含める）
agent_tools = []
for skill in skills:
    if skill.tier == SkillTier.SANDBOX and skill.name not in system_skills:
        continue
    try:
        tools = skill.get_tools()
        agent_tools.extend(tools)
    except Exception as e:
        print(f"Warning: {skill.name} のツールロードに失敗しました: {e}", file=sys.stderr)

# 開発スクリプトをシェル経由で実行するためのツールセットを追加
agent_tools.append(EnvironmentToolset(environment=LocalEnvironment()))

# スキル一覧サマリー (Level 1 Progressive Disclosure)
skills_summary_lines = []
for s in skills:
    if s.tier != SkillTier.SANDBOX or s.name in system_skills:
        skills_summary_lines.append(f"- **{s.name}**: {s.description}")
skills_summary_text = "\n".join(skills_summary_lines)

instruction_text = f"""あなたは評価駆動開発（EDD）および自己進化型スキル開発を自律遂行する統合エージェントです。
Anthropic 公式標準の Progressive Disclosure（段階的情報開示）および Markdown-First 原則に従って動作してください。

## 利用可能なスキル一覧 (Level 1 Metadata)
{skills_summary_text}

## 動作原則 (Progressive Disclosure)
1. ユーザーの要求に合致するスキルを上記一覧から選択する。
2. 必要に応じて対象スキルの `SKILL.md` を読み込み、意思決定ツリーと手順指示を確認する。
3. `scripts/` 配下のスクリプトを実行して決定論的にタスクを遂行する。
4. テスト・評価・自己修復ループは `skill-evaluator` および `skill-optimizer` を通じて自律的に実行する。
"""

root_agent = Agent(
    model='gemini-2.5-flash',
    name='evaluation_driven_development_agent',
    description='Google ADK と Anthropic スキル標準を融合した、自律的にスキルを開発・評価・統合する自己進化型エージェント',
    instruction=instruction_text,
    tools=agent_tools
)
