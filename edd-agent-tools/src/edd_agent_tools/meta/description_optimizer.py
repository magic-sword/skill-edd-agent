"""
Description Optimizer (Description Tuning Loop)

ホワイトペーパー Section 6 (p.36-37, Fig 10) 準拠：
エージェントスキルの Frontmatter description（ルーティングアルゴリズム）を
正例・負例トリガーデータセットに基づいて自動反復チューニングし、
90%以上のトリガー精度（Trigger Accuracy）を達成する最適化エンジン。
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from edd_agent_tools.core.entity import Skill
from edd_agent_tools.models import EvalRunResult, SkillFrontmatter
from edd_agent_tools.evaluation.simulation_runner import SimulationEvalRunner


class DescriptionOptimizer:
    """スキルの Frontmatter description を自動チューニング・改善するエンジン。"""

    def __init__(self, target_accuracy: float = 0.9, max_iterations: int = 5):
        self.target_accuracy = target_accuracy
        self.max_iterations = max_iterations
        self.sim_runner = SimulationEvalRunner()

    def optimize_description(
        self,
        skill: Skill,
        trigger_dataset: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """トリガー評価データセットに基づき、description を反復最適化します。

        Args:
            skill: 対象の Skill オブジェクト。
            trigger_dataset: 正例・負例を含むトリガー評価データセット。
            dry_run: True の場合、ファイル変更を行わず提案のみ返却。

        Returns:
            Dict[str, Any]: 最適化結果とイテレーション履歴。
        """
        cases = trigger_dataset.get("eval_cases") or trigger_dataset.get("cases") or []
        if not cases:
            return {"status": "skipped", "message": "No trigger cases provided."}

        initial_res = self.sim_runner.run_tests(skill=skill, eval_set_data=trigger_dataset)
        history = [{"iteration": 0, "accuracy": initial_res.accuracy, "description": skill.description}]

        if initial_res.accuracy >= self.target_accuracy:
            return {
                "status": "already_optimal",
                "accuracy": initial_res.accuracy,
                "final_accuracy": initial_res.accuracy,
                "initial_accuracy": initial_res.accuracy,
                "optimized_description": skill.description,
                "history": history,
                "message": f"Initial trigger accuracy ({initial_res.accuracy:.1%}) already meets target ({self.target_accuracy:.1%})."
            }

        current_desc = skill.description
        best_desc = current_desc
        best_acc = initial_res.accuracy

        def _get_input(c: Dict[str, Any]) -> str:
            u_input = c.get("user_input") or c.get("input") or ""
            if not u_input and "conversation" in c:
                conv = c.get("conversation", [])
                if conv and isinstance(conv, list):
                    first_turn = conv[0]
                    parts = first_turn.get("user_content", {}).get("parts", [])
                    if parts and isinstance(parts, list):
                        u_input = parts[0].get("text", "")
            return u_input

        def _is_positive(c: Dict[str, Any]) -> bool:
            if "should_trigger" in c:
                return bool(c.get("should_trigger"))
            exp_skill = c.get("expected_skill")
            return bool(exp_skill and (exp_skill == skill.name or exp_skill.replace("-", "_") == skill.name.replace("-", "_")))

        # 失敗したケースの分析
        pos_triggers = [_get_input(c) for c in cases if _is_positive(c)]
        neg_triggers = [_get_input(c) for c in cases if not _is_positive(c)]

        # キーワードの抽出とチューニング
        for iteration in range(1, self.max_iterations + 1):
            # 新しい description の合成（ホワイトペーパー Appendix A: Minimal SKILL.md 準拠）
            tuned_desc = self._synthesize_description(
                skill_name=skill.name,
                current_desc=current_desc,
                pos_triggers=pos_triggers,
                neg_triggers=neg_triggers
            )

            # 一時的に description を適用してシミュレーション
            original_desc = skill.description
            skill.spec.frontmatter.description = tuned_desc
            test_res = self.sim_runner.run_tests(skill=skill, eval_set_data=trigger_dataset)

            history.append({
                "iteration": iteration,
                "accuracy": test_res.accuracy,
                "description": tuned_desc
            })

            if test_res.accuracy > best_acc:
                best_acc = test_res.accuracy
                best_desc = tuned_desc

            if best_acc >= self.target_accuracy:
                break

            current_desc = tuned_desc

        # 最終適用
        if not dry_run and best_acc > initial_res.accuracy:
            self._update_skill_md_description(skill.spec_path, best_desc)
            skill.spec.frontmatter.description = best_desc
            status = "improved"
        else:
            skill.spec.frontmatter.description = original_desc
            status = "dry_run" if dry_run else "no_improvement"

        return {
            "status": status,
            "initial_accuracy": initial_res.accuracy,
            "final_accuracy": best_acc,
            "target_accuracy": self.target_accuracy,
            "improved": best_acc > initial_res.accuracy,
            "optimized_description": best_desc,
            "history": history
        }

    def _synthesize_description(
        self,
        skill_name: str,
        current_desc: str,
        pos_triggers: List[str],
        neg_triggers: List[str]
    ) -> str:
        """ホワイトペーパーの Frontmatter 規約に基づき、シャープな description を生成。"""
        # 第一文: 動詞起点 (Verb-led sentence)
        first_line = current_desc.strip().split("\n")[0] if current_desc else f"Provides automated tools for {skill_name}."
        
        # When to use 句
        when_clause = f"Use this skill when the user asks to {', '.join(pos_triggers[:3])}." if pos_triggers else ""
        
        # When NOT to use 句
        anti_clause = f"Do NOT use for {', '.join(neg_triggers[:2])}." if neg_triggers else ""

        parts = [first_line]
        if when_clause:
            parts.append(when_clause)
        if anti_clause:
            parts.append(anti_clause)

        return " ".join(parts)

    def _update_skill_md_description(self, spec_path: str, new_description: str):
        """SKILL.md ファイルの YAML Frontmatter description を更新します。"""
        if not os.path.exists(spec_path):
            return

        content = Path(spec_path).read_text(encoding="utf-8")
        # frontmatter の description: フィールドを正規表現で置換
        pattern = r"(description:\s*\|?\s*\n?)(?:[ \t]+[^\n]+\n*)+"
        if re.search(pattern, content):
            # 複数行または単一行の置換
            replacement = f"description: |\n  {new_description}\n"
            new_content = re.sub(pattern, replacement, content, count=1)
        else:
            # 単純な置換
            new_content = re.sub(r"description:.*?\n", f"description: {new_description}\n", content, count=1)

        Path(spec_path).write_text(new_content, encoding="utf-8")
