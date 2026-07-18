from edd_agent_tools.evaluation import EvalCaseSet

class EvalCaseSetWriter:
    """EvalCaseSetオブジェクトをJSON文字列に変換するクラス。"""

    def convert_to_json_string(self, eval_case_set: EvalCaseSet) -> str:
        """
        EvalCaseSetオブジェクトをEvalCaseSetフォーマットのJSON文字列に変換します。

        Args:
            eval_case_set: 変換するEvalCaseSetオブジェクト。

        Returns:
            EvalCaseSetフォーマットのJSON文字列。
        """
        return eval_case_set.model_dump_json(indent=2)
