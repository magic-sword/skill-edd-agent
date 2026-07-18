from pathlib import Path
from edd_agent_tools.evaluation import TrajectoryEvalSet

class TestCaseWriter:
    """生成されたテストケースをファイルに書き出す責任を持つクラス。"""

    def write_eval_case_set(self, output_path: str, eval_set: TrajectoryEvalSet) -> None:
        """
        生成されたテストケース（TrajectoryEvalSetフォーマット）をJSONファイルとして指定されたパスに書き出します。

        Args:
            output_path: テストケースを保存するファイルのパス。
            eval_set: TrajectoryEvalSetオブジェクト。
        """
        output_file_path = Path(output_path)
        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(eval_set.model_dump_json(indent=2))
        except Exception as e:
            raise Exception(f"テストケースの書き込み中にエラーが発生しました: {e}")
