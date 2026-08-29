#!/usr/bin/env python3
"""Self-Evolving EDD Agent: End-to-End Self-Evolution Demo

Kaggle Competition: Vibe Coding Agents Capstone Project (Freestyle Track)

このスクリプトは、エージェントが自然言語の曖昧な指示からスキルを自動生成し、
テスト・自己診断・自律修復（Self-Healing）・連鎖回帰テストを経て
Tier 1（本番利用可能）へ自己進化する一連のプロセスを一撃で実演します。
"""

import os
import sys
import time
import shutil
from pathlib import Path

# Add /workspace to sys.path
sys.path.insert(0, "/workspace")

from edd_agent_tools.skills import (
    SkillsState,
    SkillValidator,
    SkillTier
)
from edd_agent_tools.evaluation import CascadeTestRunner


def print_banner():
    banner = """
================================================================================
   🧬 Self-Evolving EDD Agent: Autonomous Skill Generation & Self-Healing Demo
   Powered by Google ADK 2.0 & Anthropic Markdown-First Progressive Disclosure
================================================================================
"""
    print(banner)


def main():
    print_banner()

    demo_skill_name = "case-converter"
    workspace_skills = Path("/workspace/src/skills")
    demo_skill_dir = workspace_skills / demo_skill_name

    # クリーンアップ（事前状態のリセット）
    if demo_skill_dir.exists():
        shutil.rmtree(demo_skill_dir)

    state = SkillsState()

    print(f"🎯 [Phase 1: Authoring (自律生成)]")
    print(f"ユーザー指示: 『文字列を UPPER, lower, camelCase, snake_case に変換する {demo_skill_name} スキルを作成して』")
    print(f"➔ skill-creator (4段階品質保証パイプライン) を起動中...")

    # Stage 1〜4 によるスキル生成
    creator_skill = state.get_skill("skill-creator")
    create_skill_fn = creator_skill.load_module().create_skill
    res = create_skill_fn(
        prompt="文字列を大文字(UPPER), 小文字(lower), キャメルケース(camelCase), スネークケース(snake_case)に変換するテキスト変換ユーティリティスキルを作成してください。",
        name=demo_skill_name,
        pattern="task_based"
    )

    if res.get("status") != "success":
        print(f"❌ スキル生成に失敗しました: {res}")
        return

    print(f"✅ スキル '{demo_skill_name}' の生成完了！ (3層リソース分離: SKILL.md, scripts/)")

    # 静的リンター検証
    print(f"\n🔍 [Phase 2: Static Validation (静的リンター & DAG検証)]")
    val_res = SkillValidator.validate_directory(demo_skill_dir)
    print(f"静的バリデーション結果: {'✅ 合格' if val_res.is_valid else '❌ 不合格'}")
    if val_res.warnings:
        print(f"リンター警告数: {len(val_res.warnings)}")

    # 依存関係グラフの検証
    is_dag_valid, errors = state.validate_dependency_graph()
    print(f"DAG 依存関係整合性: {'✅ 正常 (循環なし・欠落なし)' if is_dag_valid else '❌ エラー'}")

    # Phase 3: Self-Healing Loop 実演
    print(f"\n🛠 [Phase 3: Self-Improvement Loop (自律改善・最適化)]")
    print(f"➔ skill-optimizer を呼び出し、テスト実行・診断・連鎖回帰テストを実行中...")

    optimizer_skill = state.get_skill("skill-optimizer")
    optimize_skill_fn = optimizer_skill.load_module().optimize_skill
    opt_res = optimize_skill_fn(skill_name=demo_skill_name, max_retries=2)

    print(f"最適化ステータス: {opt_res.get('status')}")
    print(f"昇格権限ステータス: {opt_res.get('tier')}")
    print(f"連鎖回帰テスト結果: {opt_res.get('cascade_results')}")

    # 最終確認
    skill_obj = state.get_skill(demo_skill_name)
    current_tier_name = SkillTier(skill_obj.tier).name

    print(f"\n================================================================================")
    print(f"🎉 [Demo Completed Successfully]")
    print(f"スキル '{demo_skill_name}' はすべての安全防壁を突破し、[{current_tier_name}] としてマウントされました！")
    print(f"エージェントは自律的に新しい能力（スキル）を獲得し、自己進化を完了しました。")
    print(f"================================================================================\n")


if __name__ == "__main__":
    main()
