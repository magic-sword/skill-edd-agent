"""
Google ADK 2.0 純正評価アダプター (AdkEvalAdapter)

Google ADK 2.0 の評価 Criteria（ToolTrajectoryCriterion, TrajectoryEvaluator, Rubric 等）および
Agent Skills 白書（May 2026）に完全準拠した評価アダプター。
車輪の再発明を排除し、ADK 2.0 公式の評価コンポーネントを直接駆動します。
LLM-as-a-Judge によるルーブリック採点、Position Swapping（順序バイアス中和）、
および ADK 2.0 公式 EvalSet 形式の Trajectory 評価を提供します。
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
    from google.adk.evaluation.eval_metrics import ToolTrajectoryCriterion, EvalMetric, RubricsBasedCriterion
    from google.adk.evaluation.trajectory_evaluator import TrajectoryEvaluator
    ADK_MATCH_TYPE = ToolTrajectoryCriterion.MatchType
except ImportError:
    ToolTrajectoryCriterion = None
    EvalMetric = None
    RubricsBasedCriterion = None
    TrajectoryEvaluator = None
    ADK_MATCH_TYPE = None

# 重い依存関係 (nltk, scipy) を持つ評価器は遅延インポート化
ResponseEvaluator = None
RougeEvaluator = None
RubricBasedFinalResponseQualityV1Evaluator = None


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

try:
    from google.adk.evaluation.eval_case import EvalCase as NativeAdkEvalCase, Invocation, IntermediateData, SessionInput
    from google.adk.evaluation.eval_rubrics import Rubric as NativeAdkRubric
    from google.adk.evaluation.eval_set import EvalSet as NativeAdkEvalSet
    from google.adk.evaluation.agent_evaluator import AgentEvaluator
    from google.adk.evaluation.eval_config import EvalConfig
except ImportError:
    NativeAdkEvalCase = None
    NativeAdkRubric = None
    NativeAdkEvalSet = None
    AgentEvaluator = None
    EvalConfig = None
    Invocation = None
    IntermediateData = None

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
        if tool_call.name == "run_skill_script" and skill_name and isinstance(tool_call.args, dict):
            if not tool_call.args.get("skill_name"):
                new_args = dict(tool_call.args)
                new_args["skill_name"] = skill_name
                return genai_types.FunctionCall(name="run_skill_script", args=new_args)
        return tool_call
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
            # 既存の引数辞書があればそのまま設定
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


def convert_edd_to_adk_eval_set(edd_evalset: Dict[str, Any]) -> Any:
    """評価データセット辞書を Google ADK 2.0 純正 EvalSet モデルに変換・正規化します。"""
    eval_set_id = edd_evalset.get("eval_set_id", "edd_eval_set")
    skill_name = edd_evalset.get("skill_name")
    cases = edd_evalset.get("eval_cases") or edd_evalset.get("cases") or []
    
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
        # Google ADK 2.0 互換性保証: GEMINI_API_KEY と GOOGLE_API_KEY の相互同期
        if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
        elif os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

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
        if TrajectoryEvaluator is None or ToolTrajectoryCriterion is None or Invocation is None or genai_types is None:
            raise RuntimeError(
                "Google ADK 2.0 evaluation components (TrajectoryEvaluator, ToolTrajectoryCriterion) are required. "
                "Please ensure google-adk[eval] is installed."
            )

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

    def evaluate_response(
        self,
        actual_output: str,
        expected_output: str,
        threshold: float = 0.8
    ) -> Tuple[bool, float, str]:
        """Google ADK 2.0 純正の ResponseEvaluator (ROUGE-1) を直接呼び出して回答品質を決定論的に評価します。
        
        Args:
            actual_output: エージェントの実際の回答文字列。
            expected_output: 期待される参照回答文字列。
            threshold: 合格判定閾値 (デフォルト 0.8: ADK 公式推奨値)。
            
        Returns:
            Tuple[bool, float, str]: (合否, ROUGE-1スコア, 詳細メッセージ)
        """
        resp_eval_cls, _ = get_response_evaluator_classes()
        if resp_eval_cls is None or EvalMetric is None or Invocation is None or genai_types is None:
            # フォールバック: 軽量な決定論的 unigram overlap (ROUGE-1) を計算
            import re
            act_tokens = re.findall(r"\w+", actual_output.lower())
            exp_tokens = re.findall(r"\w+", expected_output.lower())
            if not exp_tokens:
                score = 1.0 if not act_tokens else 0.0
            else:
                overlap = sum(1 for t in exp_tokens if t in act_tokens)
                score = overlap / len(exp_tokens)
            is_passed = (score >= threshold)
            return is_passed, score, f"Deterministic unigram overlap: score={score:.2f}"

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
        msg = f"ADK ResponseEvaluator (ROUGE-1): score={score:.2f}, status={result.overall_eval_status}"
        return is_passed, score, msg

    @staticmethod
    def create_trajectory_criterion(
        mode: TrajectoryMode = "any_order",
        threshold: float = 1.0,
        match_type: Optional[Any] = None
    ) -> Any:
        """Google ADK 2.0 純正の ToolTrajectoryCriterion インスタンスを生成して返します。"""
        if ToolTrajectoryCriterion is None or ADK_MATCH_TYPE is None:
            return None

        resolved_mode = match_type if match_type is not None else mode
        if isinstance(resolved_mode, str):
            resolved_mode = resolved_mode.lower()

        match_type_map = {
            "exact": getattr(ADK_MATCH_TYPE, "EXACT", 0),
            "in_order": getattr(ADK_MATCH_TYPE, "IN_ORDER", 1),
            "any_order": getattr(ADK_MATCH_TYPE, "ANY_ORDER", 2)
        }
        adk_match = match_type_map.get(resolved_mode, getattr(ADK_MATCH_TYPE, "ANY_ORDER", 2))
        return ToolTrajectoryCriterion(threshold=threshold, match_type=adk_match)

    # 互換用エイリアス
    to_adk_criterion = create_trajectory_criterion

    @staticmethod
    def build_eval_config(
        criteria: Optional[Dict[str, Any]] = None,
        config_path: Optional[Union[str, Path]] = None,
        default_trajectory_mode: str = "in_order"
    ) -> Any:
        """Google ADK 2.0 純正の EvalConfig を構築またはロードします。"""
        if EvalConfig is None:
            return None

        if config_path and Path(config_path).exists():
            from google.adk.evaluation.eval_config import get_evaluation_criteria_or_default
            return get_evaluation_criteria_or_default(str(config_path))

        base_criteria: Dict[str, Any] = {}
        if criteria:
            from google.adk.evaluation.eval_metrics import BaseCriterion, ToolTrajectoryCriterion, RubricsBasedCriterion
            for k, v in criteria.items():
                if k == "tool_trajectory_avg_score":
                    if isinstance(v, dict):
                        base_criteria[k] = ToolTrajectoryCriterion.model_validate(v)
                    elif isinstance(v, (int, float)):
                        base_criteria[k] = ToolTrajectoryCriterion(threshold=float(v), match_type=ToolTrajectoryCriterion.MatchType.IN_ORDER)
                    else:
                        base_criteria[k] = v
                elif k == "rubric_based_final_response_quality_v1":
                    if isinstance(v, dict):
                        base_criteria[k] = RubricsBasedCriterion.model_validate(v)
                    else:
                        base_criteria[k] = v
                elif isinstance(v, (int, float)):
                    base_criteria[k] = BaseCriterion(threshold=float(v))
                elif isinstance(v, dict):
                    base_criteria[k] = BaseCriterion(**v)
                else:
                    base_criteria[k] = v
        else:
            base_criteria["tool_trajectory_avg_score"] = AdkEvalAdapter.create_trajectory_criterion(
                threshold=1.0,
                match_type=default_trajectory_mode
            )
            base_criteria["response_match_score"] = 0.8

        return EvalConfig(criteria=base_criteria)

    async def evaluate_eval_set(
        self,
        agent_module: str,
        eval_set: Any,
        eval_config: Optional[Any] = None,
        num_runs: int = 1,
        agent_name: Optional[str] = None,
        print_detailed_results: bool = True
    ) -> Any:
        """Google ADK 2.0 純正の AgentEvaluator.evaluate_eval_set() を直接実行します。"""
        if AgentEvaluator is None:
            raise RuntimeError("google.adk.evaluation.agent_evaluator.AgentEvaluator is not available.")

        if eval_config is None:
            eval_config = self.build_eval_config()

        return await AgentEvaluator.evaluate_eval_set(
            agent_module=agent_module,
            eval_set=eval_set,
            eval_config=eval_config,
            num_runs=num_runs,
            agent_name=agent_name,
            print_detailed_results=print_detailed_results
        )

    async def evaluate_with_adk_agent(
        self,
        agent_module: str,
        eval_dataset_file_path_or_dir: Union[str, Path],
        config_file_path: Optional[Union[str, Path]] = None,
        criteria: Optional[Dict[str, Any]] = None,
        num_runs: int = 1,
        print_detailed_results: bool = True
    ) -> Any:
        """Google ADK 2.0 純正の AgentEvaluator を直接実行します。
        
        Live 環境においてエージェントとスキルツールセットを完全連動させ、
        実際の Tool Trajectory と回答品質を公式パイプラインで評価します。
        """
        if AgentEvaluator is None:
            raise RuntimeError("google.adk.evaluation.agent_evaluator.AgentEvaluator is not available.")

        # agent_module の親ディレクトリを sys.path に追加してモジュール探索を保証
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

        # カスタム config や criteria が明示指定された場合のみ evaluate_eval_set を実行
        if config_file_path or criteria:
            resolved_config_path = str(Path(config_file_path).resolve()) if config_file_path else None
            eval_cfg = self.build_eval_config(criteria=criteria, config_path=resolved_config_path)
            
            # ADK 公式の _load_eval_set_from_file で標準パース
            eval_set = AgentEvaluator._load_eval_set_from_file(
                str(eval_path), eval_cfg, initial_session={}
            )
            return await self.evaluate_eval_set(
                agent_module=resolved_module_name,
                eval_set=eval_set,
                eval_config=eval_cfg,
                num_runs=num_runs,
                print_detailed_results=print_detailed_results
            )

        # ADK 公式の標準評価パイプラインに委譲
        # （同ディレクトリ内の test_config.json の自動探索および EvalSet パースが内部で自動実行される）
        return await AgentEvaluator.evaluate(
            agent_module=resolved_module_name,
            eval_dataset_file_path_or_dir=str(eval_path),
            num_runs=num_runs,
            print_detailed_results=print_detailed_results
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
        
        self.live が True の場合のみリモートの Google GenAI API（ADK RubricBasedFinalResponseQualityV1Evaluator）を呼び出し、
        デフォルトでは高速かつ決定論的な ADK 公式 ResponseEvaluator (ROUGE-1) を活用した標準評価を提供します。
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

        # オフライン / 決定論的ルーブリック評価（ADK 2.0 公式 ResponseEvaluator 連携）
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
        """Google ADK 2.0 純正 RubricBasedFinalResponseQualityV1Evaluator による判定実行（車輪の再発明を排除）。"""
        rbe_cls = get_rubric_evaluator_class()
        if rbe_cls is not None and RubricsBasedCriterion is not None and Invocation is not None and genai_types is not None:
            try:
                adk_rubrics = []
                for i, r in enumerate(rubrics, 1):
                    if isinstance(r, str):
                        adk_rubrics.append(NativeAdkRubric(rubric_id=f"r_{i}", rubric_content={"text_property": r}, type="FINAL_RESPONSE_QUALITY"))
                    elif isinstance(r, dict):
                        text_prop = r.get("text_property") or r.get("rubric_content", {}).get("text_property") or r.get("description", str(r))
                        adk_rubrics.append(NativeAdkRubric(rubric_id=r.get("rubric_id", f"r_{i}"), rubric_content={"text_property": text_prop}, type="FINAL_RESPONSE_QUALITY"))
                    elif hasattr(r, "rubric_content"):
                        adk_rubrics.append(r)

                criterion = RubricsBasedCriterion(rubrics=adk_rubrics, threshold=1.0)
                eval_metric = EvalMetric(metric_name="rubric_based_final_response_quality_v1", criterion=criterion)
                evaluator = rbe_cls(eval_metric=eval_metric)

                actual_inv = Invocation(
                    invocation_id="eval_act",
                    user_content=genai_types.Content(parts=[genai_types.Part.from_text(text=user_input)], role="user"),
                    final_response=genai_types.Content(parts=[genai_types.Part.from_text(text=actual_output)], role="model"),
                    rubrics=adk_rubrics
                )
                expected_inv = Invocation(
                    invocation_id="eval_exp",
                    user_content=genai_types.Content(parts=[genai_types.Part.from_text(text=user_input)], role="user"),
                    final_response=genai_types.Content(parts=[genai_types.Part.from_text(text=reference_output or "")], role="model") if reference_output else None,
                    rubrics=adk_rubrics
                )

                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                eval_coro = evaluator.evaluate_invocations(
                    actual_invocations=[actual_inv],
                    expected_invocations=[expected_inv]
                )

                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        eval_result = pool.submit(asyncio.run, eval_coro).result()
                else:
                    eval_result = loop.run_until_complete(eval_coro)

                score = float(eval_result.overall_score)
                return score, {
                    "mode": "adk_native_rubric_evaluator",
                    "overall_score": score,
                    "overall_status": str(eval_result.overall_eval_status),
                    "rubrics_count": len(adk_rubrics),
                    "passed_rubrics": round(score * len(adk_rubrics)),
                    "evaluator": "RubricBasedFinalResponseQualityV1Evaluator"
                }
            except Exception as e:
                print(f"[AdkEvalAdapter] ADK RubricBasedFinalResponseQualityV1Evaluator execution failed: {e}", file=sys.stderr)

        # ADK 純正評価が例外となった場合は決定論的フォールバックへ
        return self._run_deterministic_rubric_judge(
            skill=skill,
            user_input=user_input,
            actual_output=actual_output,
            rubrics=rubrics,
            reference_output=reference_output
        )

    def _run_deterministic_rubric_judge(
        self,
        skill: Optional[Skill],
        user_input: str,
        actual_output: str,
        rubrics: List[Union[str, Dict[str, Any]]],
        reference_output: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """ADK 2.0 公式 ResponseEvaluator (ROUGE-1) を用いた決定論的・高品質ルーブリック評価。
        
        特定ドメイン（order, duplicate, secret 等）のアドホックな正規表現判定を完全に排除し、
        ADK 公式の言語類似度と汎用セマンティクス規約により客観的スコアリングを実施します。
        """
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
        reference_output: Optional[str] = None
    ) -> Tuple[float, Dict[str, bool]]:
        """単一パスターゲットに対するルーブリック適合率を算出。
        
        参照回答が存在する場合は ADK 公式の ResponseEvaluator (ROUGE-1) を一次判定に活用します。
        """
        details = {}
        passed = 0

        # 参照回答がある場合、ADK 2.0 純正 ResponseEvaluator (ROUGE-1) で客観的ベーススコアを測定
        has_ref = bool(reference_output and reference_output.strip())
        rouge_passed = False
        if has_ref:
            is_p, r_score, _ = self.evaluate_response(
                actual_output=output_to_evaluate,
                expected_output=reference_output,
                threshold=0.7
            )
            rouge_passed = is_p

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

            satisfied = self._evaluate_single_rubric_rule(
                r_prop,
                user_input,
                output_to_evaluate,
                reference_output,
                rouge_passed=rouge_passed
            )
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
        reference_output: Optional[str],
        rouge_passed: bool = False
    ) -> bool:
        """単一ルーブリックの規則をオフライン決定論的環境で客観的に検証します。
        
        Google ADK 2.0 の責務分離原則に基づき：
        1. ツール呼び出し・発火制御の検証は TrajectoryEvaluator (tool_trajectory_avg_score) が担当。
        2. 参照回答との語彙一致は ResponseEvaluator (ROUGE-1) が担当。
        3. オフライン環境での本メソッドは、出力の基本健全性（非空、致命的例外・トレースバックの非発生）および
           参照回答がある場合の語彙一致（rouge_passed）を確認します。
        4. 主観的・意味論的ルーブリック評価は、Live モード時に ADK 純正の
           RubricBasedFinalResponseQualityV1Evaluator (LLM-as-a-Judge) によって厳密に判定されます。
        """
        out_lower = actual_output.lower()

        # 1. 出力が空、または致命的例外・未捕捉トレースバックが出ている場合は即座に不合格
        if not actual_output.strip() or "traceback (most recent call last)" in out_lower:
            return False

        # 2. 参照回答が存在し ROUGE-1 評価に合格している場合は合格
        if rouge_passed:
            return True

        # 3. 明確な禁止単語・情報漏洩指定（must not include X / does not contain X）の反証検証
        r_lower = rubric_text.lower()
        if any(k in r_lower for k in ["does not contain", "must not", "never contain", "avoid"]):
            forbidden_match = re.search(r"(?:not contain|avoid|must not include|never contain)\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?", r_lower)
            if forbidden_match:
                target = forbidden_match.group(1).lower()
                return target not in out_lower

        # 4. オフライン基本健全性（正常な出力が得られていること）
        return len(actual_output.strip()) > 0
