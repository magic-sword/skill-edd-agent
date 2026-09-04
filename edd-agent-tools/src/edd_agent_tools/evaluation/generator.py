"""
Evaluation Set Generator - Google ADK 2.0 公式 EvalSet / EvalConfig 雛形生成エンジン
SKILL.md および scripts/ の構造定義から、Google ADK 2.0 公式 EvalSet（*.test.json）および
公式 test_config.json（EvalConfig）のスケルトンを完全決定論的に生成・保存します。
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
    """Google ADK 2.0 公式規格準拠の決定論的評価セットジェネレータ"""

    def generate_edd_tests(self, skill_name: str, output_path: str) -> bool:
        """白書 Snippet 3 形式準拠の単一真実源 (SSOT) 評価ケース（正例3件＋負例3件）を生成する。"""
        state = SkillsState()
        skill = state.get_skill(skill_name)
        trigger_examples = []
        when_not_to_use = []
        if skill and skill.spec:
            trigger_examples = getattr(skill.spec, "when_to_use", None) or getattr(skill.spec, "concrete_trigger_examples", None) or []
            when_not_to_use = getattr(skill.spec, "when_not_to_use", None) or []

        _, script_names = _load_skill_context(skill_name)
        main_script = f"scripts/{script_names[0]}" if script_names else f"scripts/{skill_name.replace('-', '_')}.py"

        # 正例ケース (3件: 白書 Section 4 必須要件)
        pos_inputs = list(trigger_examples) if trigger_examples else []
        default_pos = [
            f"Please run {skill_name} on the input data",
            f"Process input using {skill_name}",
            f"Execute {skill_name} workflow"
        ]
        while len(pos_inputs) < 3:
            pos_inputs.append(default_pos[len(pos_inputs)])

        eval_cases = []
        for idx, inp in enumerate(pos_inputs[:3], 1):
            cid = f"{skill_name.replace('-', '_')}_edd_{idx:03d}"
            args_payload = ["--help"] if idx == 1 else {"input": "sample"}
            eval_cases.append({
                "eval_id": cid,
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
            "eval_cases": eval_cases
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def generate_test_config(self, skill_name: str, output_path: str) -> bool:
        """Google ADK 2.0 公式 EvalConfig (test_config.json) を生成する。"""
        data = {
            "criteria": {
                "tool_trajectory_avg_score": {
                    "threshold": 1.0,
                    "match_type": "IN_ORDER"
                },
                "rubric_based_final_response_quality_v1": {
                    "threshold": 0.8,
                    "rubrics": [
                        {
                            "rubric_id": "general_quality",
                            "rubric_content": {
                                "text_property": "The final response accurately satisfies the user intent cleanly without conversational filler."
                            }
                        }
                    ],
                    "judge_model_options": {
                        "judge_model": "gemini-2.5-flash",
                        "num_samples": 3
                    }
                }
            }
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def generate_adversarial_tests(self, skill_name: str, output_path: str) -> bool:
        """敵対的・境界値テストケース雛形を生成する（Google ADK 2.0 公式 EvalSet 準拠）。"""
        _, script_names = _load_skill_context(skill_name)
        main_script = f"scripts/{script_names[0]}" if script_names else f"scripts/{skill_name.replace('-', '_')}.py"

        data = {
            "eval_set_id": f"{skill_name}_adversarial_eval",
            "name": f"{skill_name}_adversarial_eval",
            "description": f"Adversarial and boundary test cases for {skill_name}",
            "skill_name": skill_name,
            "eval_cases": [
                {
                    "eval_id": f"{skill_name}_adv_empty_input",
                    "conversation": [
                        {
                            "invocation_id": f"inv_{skill_name}_adv_01",
                            "user_content": {
                                "role": "user",
                                "parts": [{"text": f"Run {skill_name} with empty input"}]
                            },
                            "final_response": {
                                "role": "model",
                                "parts": [{"text": "Error: Input cannot be empty."}]
                            },
                            "intermediate_data": {
                                "tool_uses": [
                                    {
                                        "name": "run_skill_script",
                                        "args": {
                                            "skill_name": skill_name,
                                            "file_path": main_script,
                                            "args": {"input": ""}
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "rubrics": [
                        {
                            "rubric_id": f"r_{skill_name}_adv_01_1",
                            "rubric_content": {"text_property": "handles empty input gracefully without unhandled exception"},
                            "type": "FINAL_RESPONSE_QUALITY"
                        }
                    ]
                },
                {
                    "eval_id": f"{skill_name}_adv_invalid_flag",
                    "conversation": [
                        {
                            "invocation_id": f"inv_{skill_name}_adv_02",
                            "user_content": {
                                "role": "user",
                                "parts": [{"text": f"Run {skill_name} with invalid parameters"}]
                            },
                            "final_response": {
                                "role": "model",
                                "parts": [{"text": "Error: Invalid argument provided."}]
                            },
                            "intermediate_data": {
                                "tool_uses": [
                                    {
                                        "name": "run_skill_script",
                                        "args": {
                                            "skill_name": skill_name,
                                            "file_path": main_script,
                                            "args": {"invalid_arg": "invalid_value"}
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "rubrics": [
                        {
                            "rubric_id": f"r_{skill_name}_adv_02_1",
                            "rubric_content": {"text_property": "reports helpful error message for invalid arguments"},
                            "type": "FINAL_RESPONSE_QUALITY"
                        }
                    ]
                }
            ]
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def generate_evalset(self, skill_name: str, test_type: str = "all", output_dir: Optional[str] = None) -> Dict[str, Any]:
        """指定されたスキルの評価セットを生成する統合エントリポイント（Google ADK 2.0 公式規格準拠）。"""
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
        types_to_run = ["edd", "config", "adversarial"] if test_type == "all" else [test_type]

        for t in types_to_run:
            if t in ("edd", "contract", "trigger", "trajectory", "golden", "judge"):
                # 単一真実源 (SSOT) 公式 EvalSet
                out_path = base_out / f"{skill_name}.test.json"
                if self.generate_edd_tests(skill_name, str(out_path)):
                    generated_files.append(str(out_path))
            elif t == "config":
                # Google ADK 2.0 公式 EvalConfig
                out_path = base_out / "test_config.json"
                if self.generate_test_config(skill_name, str(out_path)):
                    generated_files.append(str(out_path))
            elif t == "adversarial":
                out_path = base_out / f"{skill_name}_adversarial.test.json"
                if self.generate_adversarial_tests(skill_name, str(out_path)):
                    generated_files.append(str(out_path))

        return {
            "status": "success" if generated_files else "failed",
            "generated_files": list(dict.fromkeys(generated_files)),
            "skill_name": skill_name
        }


def generate_evalset(skill_name: str, test_type: str = "all", output_dir: Optional[str] = None) -> Dict[str, Any]:
    """モジュールレベル関数"""
    gen = EvalSetGenerator()
    return gen.generate_evalset(skill_name, test_type=test_type, output_dir=output_dir)
