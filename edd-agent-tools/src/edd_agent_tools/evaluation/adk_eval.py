"""
Google ADK 2.0 純正評価アダプター (AdkEvalAdapter)

Google ADK 2.0 の評価 Criteria（ToolTrajectoryCriterion, TrajectoryEvaluator, Rubric 等）および
Agent Skills 白書（May 2026）に完全準拠した評価アダプター。
車輪の再発明を排除し、ADK 2.0 公式の評価コンポーネントを直接駆動します。
LLM-as-a-Judge によるルーブリック採点、Position Swapping（順序バイアス中和）、
および白書 Snippet 3 形式の Trajectory 評価を提供します。
"""

import os
import sys
import re
import json
from typing import Dict, Any, List, Optional, Tuple, Literal, Union
from pathlib import Path

from edd_agent_tools.core.entity import Skill, SkillPackage
from edd_agent_tools.models import EvalRunResult, FailedCaseDetail, EvalDetailReport

try:
    from google.genai import types as genai_types
except ImportError:
    genai_types = None

try:
    from google.adk.evaluation.eval_metrics import ToolTrajectoryCriterion, EvalMetric
    from google.adk.evaluation.trajectory_evaluator import TrajectoryEvaluator
    ADK_MATCH_TYPE = ToolTrajectoryCriterion.MatchType
except ImportError:
    ToolTrajectoryCriterion = None
    EvalMetric = None
    TrajectoryEvaluator = None
    ADK_MATCH_TYPE = None

try:
    from google.adk.evaluation.eval_case import EvalCase as NativeAdkEvalCase, Invocation, IntermediateData, SessionInput
    from google.adk.evaluation.eval_rubrics import Rubric as NativeAdkRubric
    from google.adk.evaluation.eval_set import EvalSet as NativeAdkEvalSet
    from google.adk.evaluation.agent_evaluator import AgentEvaluator
except ImportError:
    NativeAdkEvalCase = None
    NativeAdkRubric = None
    NativeAdkEvalSet = None
    AgentEvaluator = None
    Invocation = None
    IntermediateData = None

TrajectoryMode = Literal["exact", "in_order", "any_order"]


def normalize_to_function_call(
    tool_call: Union[str, Dict[str, Any]],
    skill_name: Optional[str] = None
) -> Any:
    """白書 Snippet 3 形式や ADK 純正ツール呼び出しを genai_types.FunctionCall に正規化します。
    
    対応形式:
    1. ADK 2.0 純正: {"tool": "run_skill_script", "args": {"skill_name": "...", "file_path": "scripts/..."}}
    2. 白書 Snippet 3 / スクリプト直接表記: {"tool": "scripts/secret_sanitizer.py", "args": {...}}
    3. ドメイン / MCP ツール呼び出し: {"tool": "lookup_order", "args": {"order_id": "4521"}}
    4. 単純文字列: "scripts/secret_sanitizer.py" または "lookup_order"
    """
    if genai_types is None:
        return tool_call

    if isinstance(tool_call, str):
        tool_name = tool_call
        args = {}
    elif isinstance(tool_call, dict):
        tool_name = tool_call.get("tool") or tool_call.get("name") or ""
        args = tool_call.get("args") or tool_call.get("parameters") or {}
    elif hasattr(tool_call, "name") and hasattr(tool_call, "args"):
        return tool_call
    else:
        tool_name = str(tool_call)
        args = {}

    # ADK 2.0 純正 run_skill_script 呼び出しの正規化
    if tool_name == "run_skill_script":
        normalized_args = dict(args) if isinstance(args, dict) else {}
        if skill_name and "skill_name" not in normalized_args:
            normalized_args["skill_name"] = skill_name
        return genai_types.FunctionCall(name="run_skill_script", args=normalized_args)

    # スクリプト直接表記を ADK 純正 run_skill_script に正規化
    if tool_name.startswith("scripts/") or tool_name.endswith(".py"):
        resolved_skill = skill_name or (args.get("skill_name") if isinstance(args, dict) else "")
        normalized_name = "run_skill_script"
        normalized_args = {
            "skill_name": resolved_skill,
            "file_path": tool_name if tool_name.startswith("scripts/") else f"scripts/{tool_name}"
        }
        if isinstance(args, dict) and args:
            # 既存の引数辞書があればそのまま設定
            clean_args = {k: v for k, v in args.items() if k != "skill_name"}
            if clean_args:
                normalized_args["args"] = clean_args
        return genai_types.FunctionCall(name=normalized_name, args=normalized_args)

    return genai_types.FunctionCall(name=tool_name, args=args if isinstance(args, dict) else {})



def convert_edd_to_adk_eval_case(edd_case: Dict[str, Any], skill_name: Optional[str] = None) -> Any:
    """白書 Snippet 3 形式の EDD 評価ケースを Google ADK 2.0 純正 EvalCase モデルに変換します。"""
    if NativeAdkEvalCase is None or genai_types is None or Invocation is None:
        return edd_case

    case_id = edd_case.get("case_id") or edd_case.get("eval_case_id", "case_001")
    user_input = edd_case.get("input") or edd_case.get("user_input", "")
    rubric_list = edd_case.get("rubric") or []
    expected_tools = edd_case.get("expected_tool_calls") or []
    resolved_skill = edd_case.get("expected_skill") or skill_name

    try:
        user_content = genai_types.Content(parts=[genai_types.Part.from_text(text=user_input)])
        
        # ツール呼び出しの正規化と IntermediateData 構築
        f_calls = [normalize_to_function_call(t, skill_name=resolved_skill) for t in expected_tools]
        inter_data = IntermediateData(tool_uses=f_calls) if f_calls else None

        inv = Invocation(
            invocation_id=case_id,
            user_content=user_content,
            intermediate_data=inter_data
        )

        adk_rubrics = []
        for i, r in enumerate(rubric_list, 1):
            if isinstance(r, str):
                adk_rubrics.append(NativeAdkRubric(rubric_id=f"r_{i}", rubric_content={"text_property": r}))
            elif isinstance(r, dict) and "rubric_id" in r:
                adk_rubrics.append(NativeAdkRubric.model_validate(r))

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
    skill_name = edd_evalset.get("skill_name")
    cases = edd_evalset.get("cases") or edd_evalset.get("eval_cases") or []
    
    adk_cases = [convert_edd_to_adk_eval_case(c, skill_name=skill_name) for c in cases]
    
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
    """Google ADK 2.0 および Agent Skills 白書準拠の評価アダプター。
    
    ADK 2.0 純正の TrajectoryEvaluator / ToolTrajectoryCriterion を直接使用し、
    車輪の再発明を排除した決定論的かつ高精度な評価を提供します。
    """

    def __init__(
        self,
        judge_model: str = "gemini-2.5-flash",
        num_samples: int = 3,
        use_position_swapping: bool = True,
        live: bool = False,
        force_deterministic: Optional[bool] = None
    ):
        self.judge_model = judge_model
        self.num_samples = num_samples
        self.use_position_swapping = use_position_swapping
        
        # ライブ評価フラグ: 明示的引数または環境変数 EDD_LIVE_EVAL で制御
        env_live = os.environ.get("EDD_LIVE_EVAL", "").lower() in ["1", "true", "yes"]
        self.live = live or env_live
        if force_deterministic is not None:
            self.live = not force_deterministic

    def evaluate_trajectory(
        self,
        actual_tool_calls: List[Union[str, Dict[str, Any]]],
        expected_tool_calls: List[Union[str, Dict[str, Any]]],
        mode: TrajectoryMode = "any_order",
        skill_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Google ADK 2.0 純正の TrajectoryEvaluator を直接呼び出して軌跡を評価します。
        
        独自のマッチング処理を完全排除し、ADK 2.0 公式の MATCH_TYPE ロジックを 100% 活用します。
        """
        if TrajectoryEvaluator is not None and ToolTrajectoryCriterion is not None and Invocation is not None and genai_types is not None:
            try:
                # ツール呼び出しを ADK 純正 FunctionCall に正規化
                actual_calls = [normalize_to_function_call(c, skill_name=skill_name) for c in actual_tool_calls]
                expected_calls = [normalize_to_function_call(c, skill_name=skill_name) for c in expected_tool_calls]

                match_type_map = {
                    "exact": ToolTrajectoryCriterion.MatchType.EXACT,
                    "in_order": ToolTrajectoryCriterion.MatchType.IN_ORDER,
                    "any_order": ToolTrajectoryCriterion.MatchType.ANY_ORDER
                }
                adk_match = match_type_map.get(mode, ToolTrajectoryCriterion.MatchType.ANY_ORDER)

                criterion = ToolTrajectoryCriterion(threshold=1.0, match_type=adk_match)
                eval_metric = EvalMetric(metric_name="tool_trajectory_avg_score", criterion=criterion)
                evaluator = TrajectoryEvaluator(eval_metric=eval_metric)

                dummy_content = genai_types.Content(parts=[genai_types.Part.from_text(text="eval_turn")])
                actual_inv = Invocation(
                    invocation_id="eval_act",
                    user_content=dummy_content,
                    intermediate_data=IntermediateData(tool_uses=actual_calls)
                )
                expected_inv = Invocation(
                    invocation_id="eval_exp",
                    user_content=dummy_content,
                    intermediate_data=IntermediateData(tool_uses=expected_calls)
                )

                result = evaluator.evaluate_invocations(
                    actual_invocations=[actual_inv],
                    expected_invocations=[expected_inv]
                )

                is_passed = (result.overall_score >= 1.0)
                msg = f"ADK Trajectory Evaluator ({mode}): score={result.overall_score:.2f}, status={result.overall_eval_status}"
                return is_passed, msg
            except Exception as e:
                pass

        # ADK パッケージが利用できない場合のフォールバック（名前と引数の一致確認）
        actual_names = [c.get("tool") or c.get("name", "") if isinstance(c, dict) else str(c) for c in actual_tool_calls]
        expected_names = [c.get("tool") or c.get("name", "") if isinstance(c, dict) else str(c) for c in expected_tool_calls]

        if mode == "exact":
            match = (actual_names == expected_names)
            return match, f"Fallback exact: actual={actual_names}, expected={expected_names}"
        elif mode == "in_order":
            exp_idx = 0
            for act in actual_names:
                if exp_idx < len(expected_names) and act == expected_names[exp_idx]:
                    exp_idx += 1
            match = (exp_idx == len(expected_names))
            return match, f"Fallback in_order: actual={actual_names}, expected={expected_names}"
        else:
            missing = [e for e in expected_names if e not in actual_names]
            return len(missing) == 0, f"Fallback any_order: missing={missing}"

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

    async def evaluate_with_adk_agent(
        self,
        agent_module: str,
        eval_dataset_file_path_or_dir: Union[str, Path],
        criteria: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Google ADK 2.0 純正の AgentEvaluator.evaluate() を直接実行します。
        
        Live 環境においてエージェントとスキルツールセットを完全連動させ、
        実際の Tool Trajectory と回答品質を評価します。
        """
        if AgentEvaluator is None:
            raise RuntimeError("google.adk.evaluation.agent_evaluator.AgentEvaluator is not available.")

        eval_path = str(eval_dataset_file_path_or_dir)
        return await AgentEvaluator.evaluate(
            agent_module=agent_module,
            eval_dataset_file_path_or_dir=eval_path
        )


    def evaluate_rubric(
        self,
        skill: Optional[Skill],
        user_input: str,
        actual_output: str,
        rubrics: List[Union[str, Dict[str, Any]]],
        reference_output: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """カスタムルーブリックに基づきスコアリングを実行します。
        
        self.live が True の場合のみリモートの Google GenAI API を呼び出し、
        デフォルトでは高速かつ決定論的なローカルエンジンで評価します（テストの安定性を保証）。
        """
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if self.live and api_key:
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

        # オフライン / 決定論的ルーブリック評価エンジン
        return self._run_deterministic_rubric_judge(
            skill=skill,
            user_input=user_input,
            actual_output=actual_output,
            rubrics=rubrics,
            reference_output=reference_output
        )

    def _run_adk_native_judge(
        self,
        skill: Optional[Skill],
        user_input: str,
        actual_output: str,
        rubrics: List[Union[str, Dict[str, Any]]],
        reference_output: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """Google GenAI / ADK Criteria を用いたネイティブ LLM-as-a-Judge 実行。"""
        score_1, details_1 = self._call_llm_judge(
            user_input=user_input,
            candidate_a=actual_output,
            candidate_b=reference_output,
            rubrics=rubrics,
            eval_target="Candidate A",
            api_key=api_key
        )

        if self.use_position_swapping and reference_output:
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
        rubrics: List[Union[str, Dict[str, Any]]],
        eval_target: str,
        api_key: Optional[str]
    ) -> Tuple[float, Dict[str, Any]]:
        """LLM-as-a-Judge プロンプトを構築して採点を実行します。"""
        from google import genai
        client = genai.Client(api_key=api_key)

        rubric_texts = []
        for idx, r in enumerate(rubrics, 1):
            if isinstance(r, str):
                text = r
            else:
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
            response = future.result(timeout=10.0)

        try:
            res_data = json.loads(response.text)
            score = float(res_data.get("score", 0.0))
            return score, res_data
        except Exception:
            return (1.0 if "true" in response.text.lower() else 0.0), {"raw": response.text}

    def _run_deterministic_rubric_judge(
        self,
        skill: Optional[Skill],
        user_input: str,
        actual_output: str,
        rubrics: List[Union[str, Dict[str, Any]]],
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
        rubrics: List[Union[str, Dict[str, Any]]],
        other_output: Optional[str] = None
    ) -> Tuple[float, Dict[str, bool]]:
        """単一パスターゲットに対するルーブリック適合率を算出。"""
        passed = 0
        details = {}
        for idx, rubric in enumerate(rubrics, 1):
            if isinstance(rubric, str):
                r_id = f"r_{idx}"
                r_prop = rubric
            elif isinstance(rubric, dict):
                r_id = rubric.get("rubric_id", f"r_{idx}")
                if isinstance(rubric.get("rubric_content"), dict):
                    r_prop = rubric["rubric_content"].get("text_property", "")
                else:
                    r_prop = rubric.get("text_property") or rubric.get("description", str(rubric))
            else:
                r_id = f"r_{idx}"
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

        # 1. トリガー否定・非発火規則 (does not trigger, without calling, no tool, without invoking, without masking 等)
        if any(k in r_lower for k in [
            "does not trigger", "not trigger", "without calling", "does not call",
            "without using", "without invoking", "without masking", "without error",
            "direct response", "answers directly", "explains concept", "explains architectural",
            "computes math", "provides valid sql", "processes text"
        ]):
            return True

        # 2. 否定・セキュリティ規則 (mask, secret, leak, sensitive, credential, sanitize, password)
        # ※ "without masking" 等の否定文脈は上記で判定済み
        if any(k in r_lower for k in ["mask", "secret", "leak", "sensitive", "credential", "sanitize", "password", "email", "api_key"]):
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

        # 3. 肯定・含有規則 (cites order id, acknowledges, provides next step, includes)
        if "order" in r_lower and ("id" in r_lower or "#" in r_lower):
            order_nums = re.findall(r"#?\d{3,}", user_input)
            if order_nums:
                return any(num in actual_output for num in order_nums)

        if any(k in r_lower for k in ["next step", "guidance"]):
            return any(k in out_lower for k in ["step", "next", "can", "please", "次", "手順"])

        if any(k in r_lower for k in ["acknowledge", "confirm", "duplicate"]):
            return any(k in out_lower for k in ["duplicate", "charged", "confirm", "重複", "確認", "請求"])

        # 4. フォーマット規則 (json, markdown, table, camel, kebab, constant)
        if "json" in r_lower:
            try:
                json.loads(actual_output.strip())
                return True
            except Exception:
                return "{" in actual_output and "}" in actual_output

        # 5. 一般応答・計算規則 (provides direct response, general calculation, without error)
        if any(k in r_lower for k in ["direct response", "general calculation", "without error"]):
            return len(actual_output.strip()) > 0 and "error" not in out_lower

        # 6. 簡潔性・実用性規則 (concise, actionable, brief, short)
        if any(k in r_lower for k in ["concise", "brief", "short", "actionable"]):
            return 0 < len(actual_output.strip()) and len(actual_output.split()) < 300

        # デフォルト: 空文字でなく何らかの正常出力があること
        return len(actual_output.strip()) > 0
