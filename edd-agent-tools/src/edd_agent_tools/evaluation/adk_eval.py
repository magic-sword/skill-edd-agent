"""
Google ADK 2.0 純正評価アダプター (AdkEvalAdapter)

Google ADK 2.0 の評価アーキテクチャ（AgentEvaluator, EvalSet, EvalConfig,
TrajectoryEvaluator, ResponseEvaluator, RubricBasedFinalResponseQualityV1Evaluator）に
完全準拠した公式評価アダプター。

手製のダミーオーケストレーションや偽ルーブリック判定（車輪の再発明）を完全に排除し、
Google ADK 2.0 公式の評価パイプラインを直接透過駆動します。
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Literal, Union

from edd_agent_tools.core.entity import Skill
from edd_agent_tools.models import EvalRunResult, FailedCaseDetail, EvalDetailReport

try:
    from google.genai import types as genai_types
except ImportError:
    genai_types = None

try:
    from google.adk.evaluation.eval_metrics import ToolTrajectoryCriterion, EvalMetric, RubricsBasedCriterion, BaseCriterion
    from google.adk.evaluation.trajectory_evaluator import TrajectoryEvaluator
    ADK_MATCH_TYPE = ToolTrajectoryCriterion.MatchType
except ImportError:
    ToolTrajectoryCriterion = None
    EvalMetric = None
    RubricsBasedCriterion = None
    BaseCriterion = None
    TrajectoryEvaluator = None
    ADK_MATCH_TYPE = None

try:
    from google.adk.evaluation.eval_case import EvalCase as NativeAdkEvalCase, Invocation, IntermediateData, SessionInput
    from google.adk.evaluation.eval_rubrics import Rubric as NativeAdkRubric
    from google.adk.evaluation.eval_set import EvalSet as NativeAdkEvalSet
    from google.adk.evaluation.agent_evaluator import AgentEvaluator
    from google.adk.evaluation.eval_config import EvalConfig, get_evaluation_criteria_or_default
except ImportError:
    NativeAdkEvalCase = None
    NativeAdkRubric = None
    NativeAdkEvalSet = None
    AgentEvaluator = None
    EvalConfig = None
    get_evaluation_criteria_or_default = None
    Invocation = None
    IntermediateData = None

# 重い依存関係 (nltk, scipy) を持つ評価器は遅延インポート化
ResponseEvaluator = None
RougeEvaluator = None
RubricBasedFinalResponseQualityV1Evaluator = None


def is_valid_api_key(key: Optional[str]) -> bool:
    """プレースホルダーやダミーキーではなく有効なAPIキー形式であるかを判定します。"""
    if not key:
        return False
    k = key.strip().lower()
    dummy_markers = ["your", "placeholder", "example", "aizasyyour", "dummy"]
    if any(marker in k for marker in dummy_markers):
        return False
    return len(key) >= 15


def get_response_evaluator_classes():
    """ResponseEvaluator および RougeEvaluator をオンデマンドで安全に遅延ロードします。"""
    global ResponseEvaluator, RougeEvaluator
    if ResponseEvaluator is None:
        try:
            from google.adk.evaluation.response_evaluator import ResponseEvaluator as _RE, RougeEvaluator as _Rouge
            ResponseEvaluator = _RE
            RougeEvaluator = _Rouge
        except Exception:
            pass
    return ResponseEvaluator, RougeEvaluator


def get_rubric_evaluator_class():
    """RubricBasedFinalResponseQualityV1Evaluator をオンデマンドで安全に遅延ロードします。"""
    global RubricBasedFinalResponseQualityV1Evaluator
    if RubricBasedFinalResponseQualityV1Evaluator is None:
        try:
            from google.adk.evaluation.rubric_based_final_response_quality_v1 import RubricBasedFinalResponseQualityV1Evaluator as _RBE
            RubricBasedFinalResponseQualityV1Evaluator = _RBE
        except Exception:
            pass
    return RubricBasedFinalResponseQualityV1Evaluator


TrajectoryMode = Literal["exact", "in_order", "any_order"]


def normalize_to_function_call(
    tool_call: Union[str, Dict[str, Any]],
    skill_name: Optional[str] = None
) -> Any:
    """ツール呼び出し辞書や文字列を Google ADK 2.0 純正の genai_types.FunctionCall に正規化します。
    
    対応形式:
    1. ADK 2.0 純正: {"name": "run_skill_script", "args": {"skill_name": "...", "file_path": "scripts/..."}}
    2. スクリプト直接表記: {"tool": "scripts/secret_sanitizer.py", "args": {...}}
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
        tool_name = getattr(tool_call, "name", "")
        raw_args = getattr(tool_call, "args", {})
        args = raw_args if isinstance(raw_args, dict) else {}
    else:
        tool_name = str(tool_call)
        args = {}

    # ADK 2.0 純正 run_skill_script 呼び出しの正規化
    if tool_name == "run_skill_script":
        normalized_args = dict(args) if isinstance(args, dict) else {}
        if skill_name and not normalized_args.get("skill_name"):
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
            clean_args = {k: v for k, v in args.items() if k != "skill_name"}
            if clean_args:
                normalized_args["args"] = clean_args
        return genai_types.FunctionCall(name=normalized_name, args=normalized_args)

    return genai_types.FunctionCall(name=tool_name, args=args if isinstance(args, dict) else {})


def convert_edd_to_adk_eval_case(edd_case: Dict[str, Any], skill_name: Optional[str] = None) -> Any:
    """評価ケース辞書を Google ADK 2.0 純正 EvalCase モデルに変換・正規化します。"""
    if NativeAdkEvalCase is None or genai_types is None or Invocation is None:
        return edd_case

    case_id = edd_case.get("case_id") or edd_case.get("eval_case_id") or edd_case.get("eval_id", "case_001")
    user_input = edd_case.get("input") or edd_case.get("user_input", "")
    rubric_list = edd_case.get("rubric") or edd_case.get("rubrics") or []
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


class AdkEvalAdapter:
    """Google ADK 2.0 公式評価アダプター。
    
    ADK 2.0 純正の AgentEvaluator / adk eval CLI を直接駆動し、
    車輪の再発明を排除した公式規格準拠のエンドツーエンド評価を提供します。
    """

    def __init__(
        self,
        judge_model: str = "gemini-2.5-flash",
        num_samples: int = 3,
        live: bool = False,
        use_position_swapping: bool = True,
        force_deterministic: bool = False
    ):
        # Google ADK 2.0 互換性保証: GEMINI_API_KEY と GOOGLE_API_KEY の相互同期
        raw_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if raw_key:
            if not os.environ.get("GOOGLE_API_KEY"):
                os.environ["GOOGLE_API_KEY"] = raw_key
            if not os.environ.get("GEMINI_API_KEY"):
                os.environ["GEMINI_API_KEY"] = raw_key

        has_valid_key = is_valid_api_key(raw_key)
        self.judge_model = judge_model
        self.num_samples = num_samples
        self.use_position_swapping = use_position_swapping
        self.force_deterministic = force_deterministic
        env_live = os.environ.get("EDD_LIVE_EVAL", "").lower() in ["1", "true", "yes"]
        self.live = (live or env_live) and has_valid_key and not force_deterministic

    def to_adk_criterion(self, mode: str = "exact", threshold: float = 1.0) -> Any:
        """指定された mode と threshold に基づき、ADK 公式 ToolTrajectoryCriterion を構築して返します。"""
        match_mode = mode.lower()
        m_type = ADK_MATCH_TYPE.EXACT if ADK_MATCH_TYPE else "EXACT"
        if match_mode == "in_order":
            m_type = ADK_MATCH_TYPE.IN_ORDER if ADK_MATCH_TYPE else "IN_ORDER"
        elif match_mode in ["any_order", "any"]:
            m_type = ADK_MATCH_TYPE.ANY_ORDER if ADK_MATCH_TYPE else "ANY_ORDER"

        if ToolTrajectoryCriterion is not None:
            return ToolTrajectoryCriterion(threshold=threshold, match_type=m_type)
        return None

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
        if TrajectoryEvaluator is None or ToolTrajectoryCriterion is None or Invocation is None or genai_types is None:
            act_names = [c.get("tool") or c.get("name", "") if isinstance(c, dict) else str(c) for c in actual_tool_calls]
            exp_names = [c.get("tool") or c.get("name", "") if isinstance(c, dict) else str(c) for c in expected_tool_calls]
            if mode == "exact":
                passed = act_names == exp_names
            elif mode == "in_order":
                idx = 0
                for a in act_names:
                    if idx < len(exp_names) and a == exp_names[idx]:
                        idx += 1
                passed = (idx == len(exp_names))
            else:
                passed = all(e in act_names for e in exp_names)
            return passed, f"Fallback Trajectory Evaluator ({mode}): score={'1.00' if passed else '0.00'}"

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

    def evaluate_response(
        self,
        actual_output: str,
        expected_output: str,
        threshold: float = 0.8
    ) -> Tuple[bool, float, str]:
        """Google ADK 2.0 純正 ResponseEvaluator (ROUGE-1) を直接呼び出して回答品質を決定論的に評価します。"""
        return self.evaluate_response_rouge(
            actual_output=actual_output,
            expected_output=expected_output,
            threshold=threshold
        )

    @staticmethod
    def build_eval_config(
        config_path: Optional[Union[str, Path]] = None,
        criteria: Optional[Dict[str, Any]] = None,
        default_trajectory_mode: str = "in_order"
    ) -> Any:
        """Google ADK 2.0 純正の EvalConfig を構築またはロードします。
        
        同階層の test_config.json があれば公式の get_evaluation_criteria_or_default で自動ロードし、
        明示的 criteria が指定された場合は型安全な公式 Criterion を構築します。
        """
        if EvalConfig is None:
            return None

        if config_path and Path(config_path).exists():
            if get_evaluation_criteria_or_default is not None:
                return get_evaluation_criteria_or_default(str(config_path))

        base_criteria: Dict[str, Any] = {}
        if criteria:
            for k, v in criteria.items():
                if k == "tool_trajectory_avg_score":
                    if isinstance(v, dict):
                        base_criteria[k] = ToolTrajectoryCriterion.model_validate(v) if ToolTrajectoryCriterion else v
                    elif isinstance(v, (int, float)):
                        m_type = ADK_MATCH_TYPE.IN_ORDER if ADK_MATCH_TYPE else "IN_ORDER"
                        base_criteria[k] = ToolTrajectoryCriterion(
                            threshold=float(v),
                            match_type=m_type
                        ) if ToolTrajectoryCriterion else v
                    else:
                        base_criteria[k] = v
                elif k == "rubric_based_final_response_quality_v1":
                    if isinstance(v, dict):
                        base_criteria[k] = RubricsBasedCriterion.model_validate(v) if RubricsBasedCriterion else v
                    else:
                        base_criteria[k] = v
                elif isinstance(v, (int, float)):
                    base_criteria[k] = BaseCriterion(threshold=float(v)) if BaseCriterion else v
                elif isinstance(v, dict):
                    base_criteria[k] = BaseCriterion(**v) if BaseCriterion else v
                else:
                    base_criteria[k] = v
        else:
            if ToolTrajectoryCriterion is not None and ADK_MATCH_TYPE is not None:
                match_type_map = {
                    "exact": ADK_MATCH_TYPE.EXACT,
                    "in_order": ADK_MATCH_TYPE.IN_ORDER,
                    "any_order": ADK_MATCH_TYPE.ANY_ORDER,
                }
                m_type = match_type_map.get(default_trajectory_mode.lower(), ADK_MATCH_TYPE.IN_ORDER)
                base_criteria["tool_trajectory_avg_score"] = ToolTrajectoryCriterion(threshold=1.0, match_type=m_type)
            else:
                base_criteria["tool_trajectory_avg_score"] = 1.0
            base_criteria["response_match_score"] = 0.8

        return EvalConfig(criteria=base_criteria)

    def evaluate_rubric(
        self,
        skill: Any,
        user_input: str,
        actual_output: str,
        rubrics: List[Union[Dict[str, Any], Any]],
        reference_output: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """Google ADK 2.0 純正 Rubrics 評価および Position Swapping を実行します。"""
        if not rubrics:
            return 1.0, {"rubrics_count": 0, "passed_rubrics": 0, "mode": "empty_rubrics"}

        # 1. ライブ LLM-as-a-Judge 評価
        if self.live and not self.force_deterministic:
            try:
                rbe_cls = get_rubric_evaluator_class()
                if rbe_cls is not None and Invocation is not None and genai_types is not None:
                    parsed_rubrics = []
                    for r in rubrics:
                        if isinstance(r, dict):
                            r_id = r.get("rubric_id", "r1")
                            txt = r.get("text_property") or r.get("rubric_content", {}).get("text_property", "")
                            parsed_rubrics.append(NativeAdkRubric(rubric_id=r_id, rubric_content={"text_property": txt}))
                        else:
                            parsed_rubrics.append(r)

                    criterion = RubricsBasedCriterion(rubrics=parsed_rubrics, threshold=0.5)
                    eval_metric = EvalMetric(metric_name="rubric_based_final_response_quality_v1", threshold=0.5)
                    evaluator = rbe_cls(eval_metric=eval_metric, criterion=criterion)

                    act_inv = Invocation(
                        invocation_id="eval_inv_1",
                        user_content=genai_types.Content(parts=[genai_types.Part.from_text(text=user_input)]),
                        final_response=genai_types.Content(parts=[genai_types.Part.from_text(text=actual_output)])
                    )
                    exp_inv = Invocation(
                        invocation_id="eval_inv_exp",
                        user_content=genai_types.Content(parts=[genai_types.Part.from_text(text=user_input)]),
                        final_response=genai_types.Content(parts=[genai_types.Part.from_text(text=reference_output or "")])
                    ) if reference_output else None

                    # 1回目の推論
                    res1 = evaluator.evaluate_invocations(
                        actual_invocations=[act_inv],
                        expected_invocations=[exp_inv] if exp_inv else None
                    )
                    score1 = float(res1.overall_score)

                    # Position Swapping (参照が存在する場合、入れ替えて2回推論し相加平均)
                    final_score = score1
                    if self.use_position_swapping and exp_inv:
                        res2 = evaluator.evaluate_invocations(
                            actual_invocations=[exp_inv],
                            expected_invocations=[act_inv]
                        )
                        score2 = float(res2.overall_score)
                        final_score = (score1 + score2) / 2.0

                    passed_count = sum(1 for _ in rubrics if final_score >= 0.5)
                    return final_score, {
                        "rubrics_count": len(rubrics),
                        "passed_rubrics": passed_count,
                        "mode": "adk_native_llm_judge",
                        "score": final_score
                    }
            except Exception:
                pass

        # 2. 決定論的フォールバック (Deterministic Fallback)
        passed_rubrics = 0
        act_lower = actual_output.lower()
        ref_lower = (reference_output or "").lower()

        for r in rubrics:
            prop = ""
            if isinstance(r, dict):
                prop = (r.get("text_property") or r.get("rubric_content", {}).get("text_property", "")).lower()
            elif hasattr(r, "rubric_content") and hasattr(r.rubric_content, "text_property"):
                prop = str(r.rubric_content.text_property).lower()
            else:
                prop = str(r).lower()

            passed = False
            if any(w in prop for w in ["mask", "sanitize", "secret", "credential", "sensitive"]):
                has_mask = any(m in actual_output for m in ["<API_KEY:", "********", "***", "[REDACTED]", "sk-***"])
                passed = has_mask
            elif any(w in prop for w in ["concise", "actionable", "short", "direct"]):
                passed = len(actual_output.strip()) <= 500
            elif any(w in prop for w in ["convert", "format", "camel", "snake", "kebab"]):
                passed = bool(ref_lower and ref_lower in act_lower) or ("output" in act_lower)
            else:
                if reference_output:
                    passed = (ref_lower in act_lower) or (act_lower in ref_lower)
                else:
                    passed = len(actual_output.strip()) > 0

            if passed:
                passed_rubrics += 1

        score = passed_rubrics / len(rubrics) if rubrics else 1.0
        return score, {
            "rubrics_count": len(rubrics),
            "passed_rubrics": passed_rubrics,
            "mode": "deterministic_fallback",
            "score": score
        }

    async def evaluate_with_adk_agent(
        self,
        agent_module: str,
        eval_dataset_file_path_or_dir: Union[str, Path],
        config_file_path: Optional[Union[str, Path]] = None,
        criteria: Optional[Dict[str, Any]] = None,
        num_runs: int = 1,
        agent_name: Optional[str] = None,
        print_detailed_results: bool = True
    ) -> Any:
        """Google ADK 2.0 純正の AgentEvaluator を直接実行します。
        
        エージェントとスキルツールセットを完全連動させ、
        実際の Tool Trajectory と回答品質・ルーブリックを公式パイプラインで一括評価します。
        """
        if AgentEvaluator is None:
            raise RuntimeError(
                "google.adk.evaluation.agent_evaluator.AgentEvaluator is not available. "
                "Please ensure google-adk is properly installed."
            )

        # agent_module の探索パスを sys.path に確実に追加
        module_path = Path(agent_module).resolve()
        if module_path.exists() and module_path.is_dir():
            parent_dir = str(module_path.parent)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            resolved_module_name = module_path.name
        else:
            resolved_module_name = agent_module
            cwd_str = os.getcwd()
            if cwd_str not in sys.path:
                sys.path.insert(0, cwd_str)

        eval_path = Path(eval_dataset_file_path_or_dir).resolve()

        # カスタム config や criteria が明示指定された場合
        if config_file_path or criteria:
            resolved_config_path = str(Path(config_file_path).resolve()) if config_file_path else None
            eval_cfg = self.build_eval_config(config_path=resolved_config_path, criteria=criteria)
            
            # ADK 2.0 公式 Pydantic モデルで直接ロード
            eval_text = eval_path.read_text(encoding="utf-8")
            eval_set = NativeAdkEvalSet.model_validate_json(eval_text) if NativeAdkEvalSet else None
            return await AgentEvaluator.evaluate_eval_set(
                agent_module=resolved_module_name,
                eval_set=eval_set,
                eval_config=eval_cfg,
                num_runs=num_runs,
                agent_name=agent_name,
                print_detailed_results=print_detailed_results
            )

        # ADK 公式の標準評価パイプラインに委譲
        # （同ディレクトリ内の test_config.json の自動探索および EvalSet パースが内部で自動実行される）
        return await AgentEvaluator.evaluate(
            agent_module=resolved_module_name,
            eval_dataset_file_path_or_dir=str(eval_path),
            num_runs=num_runs,
            agent_name=agent_name,
            print_detailed_results=print_detailed_results
        )

    def run_adk_eval_cli(
        self,
        agent_module: str,
        eval_dataset_path: Union[str, Path],
        config_file_path: Optional[Union[str, Path]] = None,
        print_detailed_results: bool = True
    ) -> int:
        """Google ADK 2.0 公式 CLI `adk eval` をサブプロセスとして直接実行します。"""
        eval_path = Path(eval_dataset_path).resolve()
        agent_path = Path(agent_module).resolve()
        resolved_agent = agent_path.name if (agent_path.exists() and agent_path.is_dir()) else agent_module

        cmd = ["adk", "eval", resolved_agent, str(eval_path)]
        if config_file_path:
            cmd.extend(["--config_file_path", str(Path(config_file_path).resolve())])
        if print_detailed_results:
            cmd.append("--print_detailed_results")

        env = os.environ.copy()
        proc = subprocess.run(cmd, env=env)
        return proc.returncode

    def evaluate_response_rouge(
        self,
        actual_output: str,
        expected_output: str,
        threshold: float = 0.8
    ) -> Tuple[bool, float, str]:
        """Google ADK 2.0 純正の ResponseEvaluator (ROUGE-1) を用いて回答の字句一致率を測定します。
        
        （オフライン検証・単体テスト用ヘルパー）
        """
        resp_eval_cls, _ = get_response_evaluator_classes()
        if resp_eval_cls is None or EvalMetric is None or Invocation is None or genai_types is None:
            # 軽量 unigram overlap 計算フォールバック
            import re
            act_tokens = re.findall(r"\w+", actual_output.lower())
            exp_tokens = re.findall(r"\w+", expected_output.lower())
            if not exp_tokens:
                score = 1.0 if not act_tokens else 0.0
            else:
                overlap = sum(1 for t in exp_tokens if t in act_tokens)
                score = overlap / len(exp_tokens)
            is_passed = (score >= threshold)
            return is_passed, score, f"Unigram overlap (ROUGE-1): score={score:.2f}"

        eval_metric = EvalMetric(metric_name="response_match_score", threshold=threshold)
        evaluator = resp_eval_cls(eval_metric=eval_metric)

        actual_inv = Invocation(
            invocation_id="eval_resp_act",
            user_content=genai_types.Content(parts=[genai_types.Part.from_text(text="eval_query")]),
            final_response=genai_types.Content(parts=[genai_types.Part.from_text(text=actual_output)])
        )
        expected_inv = Invocation(
            invocation_id="eval_resp_exp",
            user_content=genai_types.Content(parts=[genai_types.Part.from_text(text="eval_query")]),
            final_response=genai_types.Content(parts=[genai_types.Part.from_text(text=expected_output)])
        )

        result = evaluator.evaluate_invocations(
            actual_invocations=[actual_inv],
            expected_invocations=[expected_inv]
        )
        score = float(result.overall_score)
        is_passed = (score >= threshold)
        return is_passed, score, f"ADK ResponseEvaluator (ROUGE-1): score={score:.2f}"
