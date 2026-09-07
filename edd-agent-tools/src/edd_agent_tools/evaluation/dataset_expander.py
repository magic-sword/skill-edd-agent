"""
Golden Dataset Expander (Evaluation Toolkit Pattern 2)

白書 Section 4 (Page 20, Table 1 & Page 26) 準拠：
Draft Tier 以上のスキルに必須となる 20〜30 件の代表的評価ケース
（Golden Dataset: 入力、期待ツール呼び出し、期待出力フォーマット、ルーブリック）を
シードケースから自律的かつ決定論的に合成・拡充・キュレーションするエンジン。
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from edd_agent_tools.state import SkillsState
from edd_agent_tools.core.entity import Skill


class GoldenDatasetExpander:
    """初期テストケースから 20〜30 ケースの Golden Dataset を合成・生成するクラス。"""

    EXPANSION_TEMPLATES = [
        # 短文クエリ
        "Quickly {action}",
        "Run {action}",
        "{action} now",
        # パラメータ・文脈付き
        "Please {action} from the input payload",
        "Can you {action} and make sure it is properly formatted?",
        "Help me {action} for production deployment",
        "Could you {action} without extra conversational filler?",
        "Execute automated pipeline to {action}",
        # ファイル・データ入力指示
        "Read the specified source and {action}",
        "Process the data string to {action}",
        # 慎重・検証指示
        "Verify input integrity and {action}",
        "Perform deterministic execution to {action}",
    ]

    NEGATIVE_EXPANSION_TEMPLATES = [
        "What are the best practices for {action} in general?",
        "Compare different libraries that can do {action}",
        "Can you write a tutorial explaining {action}?",
        "Tell me the history of computing related to {action}",
        "Summarize how {action} works under the hood without calling tools",
        "What are the security implications of {action}?",
    ]

    def __init__(self, state: Optional[SkillsState] = None):
        self.state = state or SkillsState()

    def expand_golden_dataset(
        self,
        skill_name: str,
        target_count: int = 20,
        output_file: Optional[Path | str] = None
    ) -> Dict[str, Any]:
        """シードケースを元に Golden Dataset (20+ ケース) を生成して保存します。"""
        skill = self.state.get_skill(skill_name)
        if not skill:
            return {"status": "error", "message": f"Skill '{skill_name}' not found."}

        # シードケースの読み込み
        seed_cases = []
        evalset_path = (
            skill.tests.get_evalset_path("composite")
            or skill.tests.get_evalset_path("trigger")
        )
        if evalset_path and Path(evalset_path).exists():
            with open(evalset_path, "r", encoding="utf-8") as f:
                tdata = json.load(f)
                seed_cases = tdata.get("eval_cases", [])

        pos_actions: List[str] = []
        neg_actions: List[str] = []

        for c in seed_cases:
            if isinstance(c, dict):
                is_neg = c.get("is_negative", False)
                conv = c.get("conversation", [])
                if conv and "user_content" in conv[0]:
                    parts = conv[0]["user_content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        t = parts[0]["text"].rstrip(".")
                        if is_neg:
                            neg_actions.append(t)
                        else:
                            pos_actions.append(t)

        if not pos_actions:
            pos_actions = [f"process with {skill.name}"]
        if not neg_actions:
            neg_actions = [f"general questions about {skill.name}"]

        golden_cases: List[Dict[str, Any]] = []
        main_script = f"scripts/{skill.name.replace('-', '_')}.py"

        # 1. 既存シードケースの引き継ぎ
        for idx, sc in enumerate(seed_cases):
            c_copy = dict(sc)
            c_copy["eval_id"] = f"{skill.name}_golden_seed_{idx+1}"
            golden_cases.append(c_copy)

        # 2. 正例の自動拡充
        template_idx = 0
        while len([c for c in golden_cases if not c.get("is_negative", False)]) < int(target_count * 0.7):
            seed_text = pos_actions[template_idx % len(pos_actions)]
            tmpl = self.EXPANSION_TEMPLATES[template_idx % len(self.EXPANSION_TEMPLATES)]
            expanded_query = tmpl.format(action=seed_text)
            case_id = f"{skill.name}_golden_pos_{len(golden_cases)+1}"

            golden_cases.append({
                "eval_id": case_id,
                "is_negative": False,
                "conversation": [
                    {
                        "invocation_id": f"inv_{case_id}",
                        "user_content": {"role": "user", "parts": [{"text": expanded_query}]},
                        "final_response": {"role": "model", "parts": [{"text": "deterministic_output"}]},
                        "intermediate_data": {
                            "tool_uses": [
                                {
                                    "name": "run_skill_script",
                                    "args": {
                                        "skill_name": skill.name,
                                        "file_path": main_script,
                                        "args": ["--help"]
                                    }
                                }
                            ]
                        }
                    }
                ],
                "rubrics": [
                    {"rubric_id": f"r_{case_id}_1", "rubric_content": {"text_property": "satisfies intent cleanly with proper tool trajectory"}},
                    {"rubric_id": f"r_{case_id}_2", "rubric_content": {"text_property": "zero conversational filler"}}
                ]
            })
            template_idx += 1

        # 3. 負例の自動拡充
        neg_idx = 0
        while len(golden_cases) < target_count:
            seed_neg = neg_actions[neg_idx % len(neg_actions)]
            tmpl = self.NEGATIVE_EXPANSION_TEMPLATES[neg_idx % len(self.NEGATIVE_EXPANSION_TEMPLATES)]
            expanded_neg = tmpl.format(action=seed_neg)
            case_id = f"{skill.name}_golden_neg_{len(golden_cases)+1}"

            golden_cases.append({
                "eval_id": case_id,
                "is_negative": True,
                "conversation": [
                    {
                        "invocation_id": f"inv_{case_id}",
                        "user_content": {"role": "user", "parts": [{"text": expanded_neg}]},
                        "final_response": {"role": "model", "parts": [{"text": "conceptual_response"}]},
                        "intermediate_data": {"tool_uses": []}
                    }
                ],
                "rubrics": [
                    {"rubric_id": f"r_{case_id}_1", "rubric_content": {"text_property": "answers conceptually without calling skill scripts"}}
                ]
            })
            neg_idx += 1

        dataset = {
            "eval_set_id": f"{skill.name}_golden_dataset",
            "skill_name": skill.name,
            "version": "1.0.0",
            "total_cases": len(golden_cases),
            "eval_cases": golden_cases
        }

        # 保存先ファイルの決定
        dest_path = (
            Path(output_file).resolve() if output_file
            else Path(skill.root_dir) / "tests" / f"{skill.name}_golden.test.json"
        )
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        return {
            "status": "success",
            "skill_name": skill_name,
            "total_cases": len(golden_cases),
            "positive_cases": len([c for c in golden_cases if not c.get("is_negative", False)]),
            "negative_cases": len([c for c in golden_cases if c.get("is_negative", False)]),
            "saved_path": str(dest_path)
        }
