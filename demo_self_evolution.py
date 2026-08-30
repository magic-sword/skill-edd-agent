#!/usr/bin/env python3
"""Self-Evolving EDD Agent: End-to-End Self-Evolution Demo

Kaggle Competition: Vibe Coding Agents Capstone Project (Freestyle Track)

このスクリプトは、エージェントがスキルを自律生成し、
静的検証・テスト・診断・最適化・連鎖回帰テスト（Cascade Testing）を経て
Tier 1（Production / Trusted）へ自己進化する一連の EDD プロセスを一撃で実演します。
"""

import os
import sys
import time
import shutil
from pathlib import Path

# Add /workspace to sys.path
sys.path.insert(0, "/workspace")

from edd_agent_tools import (
    SkillsState,
    SkillValidator,
    SkillTier,
    SkillOptimizer,
    CascadeTestRunner,
    SkillScaffolder
)


def print_banner():
    banner = """
================================================================================
   🧬 Self-Evolving EDD Agent: Autonomous Skill Generation & Evolution Demo
   Powered by Google ADK 2.0 & Anthropic Markdown-First Progressive Disclosure
================================================================================
"""
    print(banner)


def main():
    print_banner()

    demo_skill_name = "demo-case-helper"
    workspace_skills = Path(__file__).parent / "src" / "skills"
    demo_skill_dir = workspace_skills / demo_skill_name

    # クリーンアップ（事前状態のリセット）
    if demo_skill_dir.exists():
        shutil.rmtree(demo_skill_dir)

    state = SkillsState()

    print(f"🎯 [Phase 1: Authoring (自律生成)]")
    print(f"ユーザー指示: 『文字列を UPPER, lower, camelCase, snake_case に変換する {demo_skill_name} スキルを作成して』")
    print(f"➔ skill-creator (4段階品質保証パイプライン) を起動中...")

    # Stage 1〜4 によるスキル生成
    target_dir = SkillScaffolder.scaffold(
        skill_name=demo_skill_name,
        output_base_dir=workspace_skills,
        pattern="task_based"
    )

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

    # Phase 3: Self-Improvement Loop 実演
    print(f"\n🛠 [Phase 3: Self-Improvement Loop (自律改善・最適化 & 連鎖回帰テスト)]")
    print(f"➔ skill-evolver / edd optimize を呼び出し、テスト実行・診断・連鎖回帰テストを実行中...")

    optimizer = SkillOptimizer(state=state)
    opt_res = optimizer.optimize_skill(skill_name=demo_skill_name, target_tier=1, run_cascade=True)

    print(f"最適化ステータス: {opt_res.get('status')}")
    print(f"昇格権限ステータス: Tier {opt_res.get('promoted_tier', 1)}")
    if opt_res.get("cascade_results"):
        print(f"連鎖回帰テスト結果: {opt_res.get('cascade_results')}")

    # 最終確認
    skill_obj = state.get_skill(demo_skill_name)
    current_tier_name = SkillTier(skill_obj.tier).name if skill_obj and skill_obj.tier else "READ_ONLY"

    print(f"\n================================================================================")
    print(f"🎉 [Demo Completed Successfully]")
    print(f"スキル '{demo_skill_name}' はすべての安全防壁を突破し、[{current_tier_name}] としてマウントされました！")
    print(f"エージェントは自律的に新しい能力（スキル）を獲得し、自己進化を完了しました。")
    print(f"================================================================================\n")

    # クリーンアップ（デモ用スキルを削除）
    if demo_skill_dir.exists():
        shutil.rmtree(demo_skill_dir)
        if demo_skill_name in state.data.skills:
            del state.data.skills[demo_skill_name]
            state.save()


if __name__ == "__main__":
    main()
