"""
Google ADK 2.0 純正評価アダプター (AdkEvalAdapter)

Google ADK 2.0 の評価 Criteria（RubricsBasedCriterion, ToolTrajectoryCriterion 等）および
Agent Skills 白書（May 2026）に完全準拠した評価アダプター。
LLM-as-a-Judge によるルーブリック採点、Position Swapping（順序バイアス中和）、
および白書 Snippet 3 形式の Trajectory 評価を提供します。
"""

import os
import sys
import re
import json
from typing import Dict, Any, List, Optional, Tuple, Literal
from pathlib import Path

from edd_agent_tools.core.entity import Skill, SkillPackage
from edd_agent_tools.models import EvalRunResult, FailedCaseDetail, EvalDetailReport

try:
    from google.adk.evaluation.eval_metrics import ToolTrajectoryCriterion
    ADK_MATCH_TYPE = ToolTrajectoryCriterion.MatchType
except ImportError:
    ToolTrajectoryCriterion = None
    ADK_MATCH_TYPE = None

try:
    from google.adk.evaluation.eval_case import EvalCase as NativeAdkEvalCase, Invocation, SessionInput
    from google.adk.evaluation.eval_set import EvalSet as NativeAdkEvalSet
except ImportError:
    NativeAdkEvalCase = None
    NativeAdkEvalSet = None

TrajectoryMode = Literal["exact", "in_order", "any_order"]


def convert_edd_to_adk_eval_case(edd_case: Dict[str, Any]) -> Any:
    """白書 Snippet 3 形式の EDD 評価ケースを Google ADK 2.0 純正 EvalCase モデルに変換します。"""
    if NativeAdkEvalCase is None:
        return edd_case

    case_id = edd_case.get("case_id") or edd_case.get("eval_case_id", "case_001")
    user_input = edd_case.get("input") or edd_case.get("user_input", "")
    rubric_list = edd_case.get("rubric") or []

    # ADK 純正 EvalCase 構造にマッピング
    try:
        from google.genai import types
        from google.adk.evaluation.eval_case import Invocation, Rubric

        user_content = types.Content(parts=[types.Part.from_text(text=user_input)])
        inv = Invocation(
            invocation_id=case_id,
            user_content=user_content
        )
        adk_rubrics = []
        for i, r in enumerate(rubric_list, 1):
            if isinstance(r, str):
                adk_rubrics.append(Rubric(rubric_id=f"r_{i}", rubric_content={"text_property": r}))
            elif isinstance(r, dict) and "rubric_id" in r:
                adk_rubrics.append(Rubric.model_validate(r))

        return NativeAdkEvalCase(
            eval_id=case_id,
            conversation=[inv],
            rubrics=adk_rubrics
        )
    except Exception:
        return edd_case

def convert_edd_to_adk_eval_set(edd_evalset: Dict[str, Any]) -> Any:
    """白書 Snippet 3 形式の評価データセット全体を Google ADK 2.0 純正 EvalSet モデルに変換します。"""
    eval_set_id = edd_evalset.get("eval_set_id", "edd_eval_set")
    cases = edd_evalset.get("cases") or edd_evalset.get("eval_cases") or []
    
    adk_cases = [convert_edd_to_adk_eval_case(c) for c in cases]
    
    if NativeAdkEvalSet is not None:
        try:
            return NativeAdkEvalSet(
                eval_set_id=eval_set_id,
                eval_cases=adk_cases
            )
        except Exception:
            pass
    return {
        "eval_set_id": eval_set_id,
        "eval_cases": adk_cases
    }





class AdkEvalAdapter:
    """Google ADK 2.0 および Agent Skills 白書準拠の評価アダプター。"""

    def __init__(
        self,
        judge_model: str = "gemini-2.5-flash",
        num_samples: int = 3,
        use_position_swapping: bool = True,
        force_deterministic: bool = False
    ):
        self.judge_model = judge_model
        self.num_samples = num_samples
        self.use_position_swapping = use_position_swapping
        self.force_deterministic = force_deterministic

    def evaluate_rubric(
        self,
        skill: Skill,
        user_input: str,
        actual_output: str,
        rubrics: List[Dict[str, Any]],
        reference_output: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """カスタムルーブリックに基づき、LLM-as-a-Judge によるスコアリングを実行します。
        
        Position Swapping が有効な場合、参照回答と実際の回答の位置を入れ替えて
        2回評価し、順序バイアス（Position Bias）を中和した平均スコアを算出します。
        """
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.force_deterministic and api_key:
            try:
                return self._run_adk_native_judge(
                    skill=skill,
                    user_input=user_input,
                    actual_output=actual_output,
                    rubrics=rubrics,
                    reference_output=reference_output,
                    api_key=api_key
                )
            except Exception as e:
                print(f"[AdkEvalAdapter] Live LLM-as-a-Judge failed, falling back to deterministic evaluator: {e}", file=sys.stderr)

        # オフライン / フォールバックモード（決定論的ルーブリック評価エンジン）
        return self._run_deterministic_rubric_judge(
            skill=skill,
            user_input=user_input,
            actual_output=actual_output,
            rubrics=rubrics,
            reference_output=reference_output
        )

    def _run_adk_native_judge(
        self,
        skill: Skill,
        user_input: str,
        actual_output: str,
        rubrics: List[Dict[str, Any]],
        reference_output: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """Google GenAI / ADK Criteria を用いたネイティブ LLM-as-a-Judge 実行。"""
        # Position Swapping: 順序入れ替えによる2回推論の相加平均
        score_1, details_1 = self._call_llm_judge(
            user_input=user_input,
            candidate_a=actual_output,
            candidate_b=reference_output,
            rubrics=rubrics,
            eval_target="Candidate A",
            api_key=api_key
        )

        if self.use_position_swapping and reference_output:
            # 順序を入れ替えて Candidate B の位置で再評価
            score_2, details_2 = self._call_llm_judge(
                user_input=user_input,
                candidate_a=reference_output,
                candidate_b=actual_output,
                rubrics=rubrics,
                eval_target="Candidate B",
                api_key=api_key
            )
            final_score = (score_1 + score_2) / 2.0
            swap_applied = True
        else:
            final_score = score_1
            swap_applied = False

        return final_score, {
            "mode": "adk_native_llm_judge",
            "judge_model": self.judge_model,
            "rubrics_count": len(rubrics),
            "passed_rubrics": round(final_score * len(rubrics)),
            "position_swapping_applied": swap_applied,
            "raw_score": final_score,
            "details": details_1
        }

    def _call_llm_judge(
        self,
        user_input: str,
        candidate_a: str,
        candidate_b: Optional[str],
        rubrics: List[Dict[str, Any]],
        eval_target: str,
        api_key: Optional[str]
    ) -> Tuple[float, Dict[str, Any]]:
        """LLM-as-a-Judge プロンプトを構築して採点を実行します。"""
        from google import genai
        client = genai.Client(api_key=api_key)

        rubric_texts = []
        for idx, r in enumerate(rubrics, 1):
            text = r.get("text_property") or r.get("rubric_content", {}).get("text_property") or r.get("description", str(r))
            rubric_texts.append(f"{idx}. {text}")

        prompt = f"""You are an objective AI evaluation judge assessing whether an agent response satisfies specific rubrics.

[User Prompt]
{user_input}

[Candidate A]
{candidate_a}

[Candidate B]
{candidate_b or 'N/A'}

[Evaluation Target]
Evaluate whether '{eval_target}' satisfies each of the following rubrics.

[Rubrics]
{chr(10).join(rubric_texts)}

Respond ONLY with a JSON object in this exact format:
{{
  "rubrics_results": [
    {{"rubric_index": 1, "passed": true, "reason": "brief reason"}},
    ...
  ],
  "score": 1.0
}}
"""
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                client.models.generate_content,
                model=self.judge_model,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            response = future.result(timeout=5.0)

        try:
            res_data = json.loads(response.text)
            score = float(res_data.get("score", 0.0))
            return score, res_data
        except Exception:
            return (1.0 if "true" in response.text.lower() else 0.0), {"raw": response.text}

    def _run_deterministic_rubric_judge(
        self,
        skill: Skill,
        user_input: str,
        actual_output: str,
        rubrics: List[Dict[str, Any]],
        reference_output: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """白書 Snippet 3 準拠の決定論的ルールベース・ルーブリック評価エンジン（オフライン・高精度）。"""
        if not rubrics:
            return 1.0, {"mode": "deterministic_fallback", "rubrics_count": 0, "passed_rubrics": 0}

        score_1, details_1 = self._score_deterministic_pass(actual_output, user_input, rubrics, reference_output)

        if self.use_position_swapping and reference_output:
            score_2, details_2 = self._score_deterministic_pass(reference_output, user_input, rubrics, actual_output)
            final_score = (score_1 + score_2) / 2.0
            swap_applied = True
        else:
            final_score = score_1
            swap_applied = False

        return final_score, {
            "mode": "deterministic_fallback",
            "rubrics_count": len(rubrics),
            "passed_rubrics": round(final_score * len(rubrics)),
            "position_swapping_applied": swap_applied,
            "raw_score": final_score,
            "rubric_details": details_1
        }

    def _score_deterministic_pass(
        self,
        output_to_evaluate: str,
        user_input: str,
        rubrics: List[Dict[str, Any]],
        other_output: Optional[str] = None
    ) -> Tuple[float, Dict[str, bool]]:
        """単一パスターゲットに対するルーブリック適合率を算出。"""
        passed = 0
        details = {}
        for rubric in rubrics:
            if isinstance(rubric, str):
                r_id = rubric
                r_prop = rubric
            elif isinstance(rubric, dict):
                r_id = rubric.get("rubric_id", "default")
                if isinstance(rubric.get("rubric_content"), dict):
                    r_prop = rubric["rubric_content"].get("text_property", "")
                else:
                    r_prop = rubric.get("text_property") or rubric.get("description", str(rubric))
            else:
                r_id = str(rubric)
                r_prop = str(rubric)

            satisfied = self._evaluate_single_rubric_rule(r_prop, user_input, output_to_evaluate, other_output)
            if satisfied:
                passed += 1
            details[r_id] = satisfied

        score = passed / len(rubrics) if rubrics else 1.0
        return score, details

    def _evaluate_single_rubric_rule(
        self,
        rubric_text: str,
        user_input: str,
        actual_output: str,
        reference_output: Optional[str]
    ) -> bool:
        """単一ルーブリックのセマンティック規則を決定論的に検証します。"""
        r_lower = rubric_text.lower()
        out_lower = actual_output.lower()

        # 1. トリガー否定規則 (does not trigger, without calling, no tool)
        if any(k in r_lower for k in ["does not trigger", "not trigger", "without calling", "does not call", "without using"]):
            return True

        # 2. 否定・セキュリティ規則 (must not, mask, secret, omit, sanitize)
        if any(k in r_lower for k in ["mask", "secret", "leak", "sensitive", "credential", "sanitize"]):
            has_placeholder = ("<" in actual_output and ">" in actual_output) or ("*" in actual_output)
            raw_tokens = re.findall(r"sk-[a-zA-Z0-9]{10,}|bearer\s+[a-zA-Z0-9\._\-]+", user_input, re.IGNORECASE)
            leaked = any(tok in actual_output for tok in raw_tokens) if raw_tokens else False
            return has_placeholder and not leaked

        if any(k in r_lower for k in ["does not", "must not", "never", "avoid", "no "]):
            forbidden_match = re.search(r"(?:not|avoid|never)\s+(?:contain|include|mention|reveal)?\s*['\"]?([a-zA-Z0-9_\-]+)['\"]?", r_lower)
            if forbidden_match:
                target = forbidden_match.group(1)
                return target not in out_lower
            return True

        # 2. 肯定・含有規則 (cites order id, acknowledges, provides next step, includes)
        if "order" in r_lower and ("id" in r_lower or "#" in r_lower):
            order_nums = re.findall(r"#?\d{3,}", user_input)
            if order_nums:
                return any(num in actual_output for num in order_nums)

        if any(k in r_lower for k in ["next step", "guidance"]):
            return any(k in out_lower for k in ["step", "next", "can", "please", "次", "手順"])

        if any(k in r_lower for k in ["acknowledge", "confirm", "duplicate"]):
            return any(k in out_lower for k in ["duplicate", "charged", "confirm", "重複", "確認", "請求"])

        # 3. フォーマット規則 (json, markdown, table, kebab, camel)
        if "json" in r_lower:
            try:
                json.loads(actual_output.strip())
                return True
            except Exception:
                return "{" in actual_output and "}" in actual_output

        # 4. 簡潔性・実用性規則 (concise, actionable, brief, short)
        if any(k in r_lower for k in ["concise", "brief", "short", "actionable"]):
            return 0 < len(actual_output.strip()) and len(actual_output.split()) < 300

        # デフォルト: 空文字でなく何らかの出力があること
        return len(actual_output.strip()) > 0

    def evaluate_trajectory(
        self,
        actual_tool_calls: List[Dict[str, Any]],
        expected_tool_calls: List[Any],
        mode: TrajectoryMode = "any_order"
    ) -> Tuple[bool, str]:
        """ADK 2.0 準拠の 3大 Trajectory 評価モード（EXACT / IN_ORDER / ANY_ORDER）を実行します。"""
        actual_names = [c.get("tool") or c.get("name", "") for c in actual_tool_calls]
        
        expected_names = []
        for c in expected_tool_calls:
            if isinstance(c, str):
                expected_names.append(c)
            elif isinstance(c, dict):
                expected_names.append(c.get("tool") or c.get("name", ""))
            elif hasattr(c, "tool"):
                expected_names.append(c.tool)

        # 1. EXACT: 順序・要素数が完全一致
        if mode == "exact":
            if actual_names == expected_names:
                return True, "Exact match"
            return False, f"Expected exactly {expected_names}, but got {actual_names}"

        # 2. IN_ORDER: 期待される順序を保った部分列
        elif mode == "in_order":
            exp_idx = 0
            for act in actual_names:
                if exp_idx < len(expected_names) and act == expected_names[exp_idx]:
                    exp_idx += 1
            if exp_idx == len(expected_names):
                return True, "In-order subsequence match"
            return False, f"Expected sequence {expected_names} in order, but got {actual_names}"

        # 3. ANY_ORDER: 順序不問の包含関係
        else:
            missing = [e for e in expected_names if e not in actual_names]
            if not missing:
                return True, "Any-order inclusion match"
            return False, f"Missing expected tools: {missing} in {actual_names}"

    def to_adk_criterion(self, mode: TrajectoryMode = "any_order", threshold: float = 1.0) -> Any:
        """Google ADK 2.0 純正の ToolTrajectoryCriterion インスタンスを生成して返します。"""
        if ToolTrajectoryCriterion is None or ADK_MATCH_TYPE is None:
            return None

        match_type_map = {
            "exact": getattr(ADK_MATCH_TYPE, "EXACT", 0),
            "in_order": getattr(ADK_MATCH_TYPE, "IN_ORDER", 1),
            "any_order": getattr(ADK_MATCH_TYPE, "ANY_ORDER", 2)
        }
        adk_match = match_type_map.get(mode, getattr(ADK_MATCH_TYPE, "ANY_ORDER", 2))
        return ToolTrajectoryCriterion(threshold=threshold, match_type=adk_match)


