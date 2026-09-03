"""
Evaluation Set Generator - 決定論的テストデータセット雛形生成エンジン
SKILL.md および scripts/ の構造定義から、Contract, Trigger, Trajectory, Golden, Judge, Adversarial
の各多層評価テストセット（.evalset.json）のスケルトンを完全決定論的に生成・保存します。
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from edd_agent_tools.state import SkillsState


def _load_skill_context(skill_name: str) -> tuple[str, List[str]]:
    """対象スキルの SKILL.md および scripts/ のスクリプト名一覧を取得する。"""
    state = SkillsState()
    skill = state.get_skill(skill_name)
    if not skill:
        raise ValueError(f"Skill '{skill_name}' was not found in SkillsState.")

    skill_md = ""
    if skill.spec_path and Path(skill.spec_path).exists():
        skill_md = Path(skill.spec_path).read_text(encoding="utf-8")

    script_names = []
    if Path(skill.scripts_dir).exists():
        for py_file in Path(skill.scripts_dir).glob("*.py"):
            if py_file.name != "__init__.py":
                script_names.append(py_file.name)

    return skill_md, script_names


class EvalSetGenerator:
    """決定論的多層評価テストセット（EDD SSOT, Trigger, Contract, Golden, Judge, Trajectory, Adversarial）ジェネレータ"""

    def generate_edd_tests(self, skill_name: str, output_path: str) -> bool:
        """白書 Snippet 3 形式準拠の単一真実源 (SSOT) 評価ケース（正例＋負例完備）を生成する。"""
        state = SkillsState()
        skill = state.get_skill(skill_name)
        trigger_examples = []
        when_not_to_use = []
        if skill and skill.spec:
            trigger_examples = getattr(skill.spec, "when_to_use", None) or getattr(skill.spec, "concrete_trigger_examples", None) or []
            when_not_to_use = getattr(skill.spec, "when_not_to_use", None) or []

        _, script_names = _load_skill_context(skill_name)
        main_script = f"scripts/{script_names[0]}" if script_names else f"scripts/{skill_name.replace('-', '_')}.py"

        eval_cases = []
        for idx, inp in enumerate(pos_inputs[:3], 1):
            cid = f"{skill_name.replace('-', '_')}_edd_{idx:03d}"
            args_payload = ["--help"] if idx == 1 else {"input": "sample"}
            eval_cases.append({
                "eval_id": cid,
                "case_id": cid,
                "expected_skill": skill_name,
                "conversation": [
                    {
                        "invocation_id": f"inv_{cid}",
                        "user_content": {
                            "role": "user",
                            "parts": [{"text": inp}]
                        },
                        "final_response": {
                            "role": "model",
                            "parts": [{"text": f"processed_{skill_name}_output"}]
                        },
                        "intermediate_data": {
                            "tool_uses": [
                                {
                                    "name": "run_skill_script",
                                    "args": {
                                        "skill_name": skill_name,
                                        "file_path": main_script,
                                        "args": args_payload
                                    }
                                }
                            ]
                        }
                    }
                ],
                "rubrics": [
                    {
                        "rubric_id": f"r_{cid}_1",
                        "rubric_content": {"text_property": f"invokes run_skill_script with {main_script} deterministically"},
                        "type": "TOOL_USE_QUALITY"
                    },
                    {
                        "rubric_id": f"r_{cid}_2",
                        "rubric_content": {"text_property": "preserves input structure and provides clean output"},
                        "type": "FINAL_RESPONSE_QUALITY"
                    }
                ],
                "session_input": {
                    "app_name": skill_name,
                    "user_id": "test_user",
                    "state": {}
                }
            })

        # 負例ケース (3件: 白書 Section 4 Page 22 必須要件 - 90% トリガー精度保証)
        neg_inputs = list(when_not_to_use) if when_not_to_use else []
        default_negs = [
            "Summarize the architectural benefits of Google ADK 2.0",
            "What is the capital of France?",
            f"Explain the conceptual design of {skill_name} without running any tools"
        ]
        while len(neg_inputs) < 3:
            neg_inputs.append(default_negs[len(neg_inputs)])

        for idx, n_inp in enumerate(neg_inputs[:3], 1):
            cid = f"{skill_name.replace('-', '_')}_edd_neg_{idx:03d}"
            eval_cases.append({
                "eval_id": cid,
                "case_id": cid,
                "expected_skill": None,
                "conversation": [
                    {
                        "invocation_id": f"inv_{cid}",
                        "user_content": {
                            "role": "user",
                            "parts": [{"text": n_inp}]
                        },
                        "final_response": {
                            "role": "model",
                            "parts": [{"text": "direct_answer"}]
                        },
                        "intermediate_data": {
                            "tool_uses": []
                        }
                    }
                ],
                "rubrics": [
                    {
                        "rubric_id": f"r_{cid}_1",
                        "rubric_content": {"text_property": f"does not trigger {skill_name}"},
                        "type": "FINAL_RESPONSE_QUALITY"
                    }
                ],
                "session_input": {
                    "app_name": skill_name,
                    "user_id": "test_user",
                    "state": {}
                }
            })

        data = {
            "eval_set_id": f"{skill_name}_edd_eval",
            "name": f"{skill_name}_edd_eval",
            "description": f"Official Google ADK 2.0 EvalSet for {skill_name}",
            "skill_name": skill_name,
            "eval_cases": eval_cases,
            "cases": eval_cases
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def generate_trigger_tests(self, skill_name: str, output_path: str) -> bool:
        """インテント分類用のトリガーテストケース（正例・負例発話）の雛形を生成する。"""
        state = SkillsState()
        skill = state.get_skill(skill_name)
        trigger_examples = []
        when_not_to_use = []
        if skill and skill.spec:
            trigger_examples = getattr(skill.spec, "when_to_use", None) or getattr(skill.spec, "concrete_trigger_examples", None) or []
            when_not_to_use = getattr(skill.spec, "when_not_to_use", None) or []

        cases = []
        if trigger_examples:
            for idx, ex in enumerate(trigger_examples, 1):
                cases.append({
                    "name": f"positive_case_{idx}",
                    "user_input": ex,
                    "expected_tools": [skill_name],
                    "should_trigger": True
                })
        else:
            cases.append({
                "name": "positive_case_1",
                "user_input": f"Please execute {skill_name} workflow",
                "expected_tools": [skill_name],
                "should_trigger": True
            })

        if when_not_to_use:
            for idx, non_ex in enumerate(when_not_to_use[:3], 1):
                cases.append({
                    "name": f"negative_case_{idx}",
                    "user_input": non_ex,
                    "expected_tools": [],
                    "should_trigger": False
                })
        else:
            cases.append({
                "name": "negative_case_1",
                "user_input": "Show me general system help",
                "expected_tools": [],
                "should_trigger": False
            })

        data = {
            "eval_set_id": f"{skill_name}_trigger_eval",
            "cases": cases
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def generate_contract_tests(self, skill_name: str, output_path: str) -> bool:
        """CLI引数・終了コードを検証する契約テストケースを生成する。"""
        _, script_names = _load_skill_context(skill_name)
        main_script = f"scripts/{script_names[0]}" if script_names else f"scripts/{skill_name.replace('-', '_')}.py"

        data = {
            "eval_set_id": f"{skill_name}_contract_eval",
            "eval_cases": [
                {
                    "eval_case_id": "test_cli_help",
                    "script_name": main_script,
                    "cli_args": ["--help"],
                    "expected_exit_code": 0,
                    "expected_stdout_contains": ["--help"]
                }
            ]
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def generate_golden_tests(self, skill_name: str, output_path: str) -> bool:
        """ゴールデンアウトプットを検証するテストケース雛形を生成する。"""
        data = {
            "eval_set_id": f"{skill_name}_golden_eval",
            "cases": [
                {
                    "name": "golden_standard_execution",
                    "input_scenario": f"Run standard workflow for {skill_name}",
                    "expected_outputs": {
                        "result_contains": [skill_name]
                    }
                }
            ]
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def generate_judge_tests(self, skill_name: str, output_path: str) -> bool:
        """LLMルーブリックジャッジ用の評価基準雛形を生成する。"""
        data = {
            "eval_set_id": f"{skill_name}_judge_eval",
            "cases": [
                {
                    "name": "judge_quality_rubric",
                    "input_prompt": f"Execute {skill_name} task",
                    "rubrics": [
                        {"criterion": "正確性 (Accuracy)", "weight": 0.4, "description": "仕様通りの出力が行われているか"},
                        {"criterion": "完全性 (Completeness)", "weight": 0.3, "description": "必要な要素が欠落していないか"},
                        {"criterion": "簡潔性 (Conciseness)", "weight": 0.3, "description": "不要な冗長性がないか"}
                    ],
                    "pass_threshold": 0.85
                }
            ]
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def generate_trajectory_tests(self, skill_name: str, output_path: str) -> bool:
        """Google ADK 準拠のツール軌跡（Tool Trajectory）評価テストケースを生成する。"""
        _, script_names = _load_skill_context(skill_name)
        main_script = script_names[0] if script_names else f"{skill_name.replace('-', '_')}.py"

        data = {
            "eval_set_id": f"{skill_name}_trajectory_eval",
            "cases": [
                {
                    "invocation_id": "inv_001",
                    "user_content": {"text": f"Please execute {skill_name}"},
                    "final_response": {"text": f"Successfully completed {skill_name}."},
                    "intermediate_data": {
                        "tool_uses": [
                            {
                                "name": main_script,
                                "args": {"input": "sample"}
                            }
                        ]
                    }
                }
            ]
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def generate_adversarial_tests(self, skill_name: str, output_path: str) -> bool:
        """敵対的・境界値テストケース雛形を生成する。"""
        data = {
            "eval_set_id": f"{skill_name}_adversarial_eval",
            "cases": [
                {
                    "name": "adv_empty_input",
                    "input_data": "",
                    "expected_behavior": "graceful_error_handling"
                },
                {
                    "name": "adv_invalid_type",
                    "input_data": 999999,
                    "expected_behavior": "graceful_error_handling"
                }
            ]
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def generate_evalset(self, skill_name: str, test_type: str = "all", output_dir: Optional[str] = None) -> Dict[str, Any]:
        """指定されたスキルの評価セットを生成する統合エントリポイント。"""
        state = SkillsState()
        skill = state.get_skill(skill_name)
        if not skill:
            return {"status": "failed", "message": f"Skill '{skill_name}' not found."}

        if output_dir:
            base_out = Path(output_dir)
        else:
            base_out = Path(skill.root_dir) / "tests"
        base_out.mkdir(parents=True, exist_ok=True)

        generated_files = []
        types_to_run = ["edd", "trigger", "contract", "golden", "judge", "trajectory", "adversarial"] if test_type == "all" else [test_type]

        for t in types_to_run:
            out_path = base_out / f"{skill_name}_{t}.evalset.json"
            success = False
            if t == "edd":
                success = self.generate_edd_tests(skill_name, str(out_path))
            elif t == "trigger":
                success = self.generate_trigger_tests(skill_name, str(out_path))
            elif t == "contract":
                success = self.generate_contract_tests(skill_name, str(out_path))
            elif t == "golden":
                success = self.generate_golden_tests(skill_name, str(out_path))
            elif t == "judge":
                success = self.generate_judge_tests(skill_name, str(out_path))
            elif t == "trajectory":
                success = self.generate_trajectory_tests(skill_name, str(out_path))
            elif t == "adversarial":
                success = self.generate_adversarial_tests(skill_name, str(out_path))

            if success:
                generated_files.append(str(out_path))

        return {
            "status": "success" if generated_files else "failed",
            "generated_files": generated_files,
            "skill_name": skill_name
        }


def generate_evalset(skill_name: str, test_type: str = "all", output_dir: Optional[str] = None) -> Dict[str, Any]:
    """モジュールレベル関数"""
    gen = EvalSetGenerator()
    return gen.generate_evalset(skill_name, test_type=test_type, output_dir=output_dir)
