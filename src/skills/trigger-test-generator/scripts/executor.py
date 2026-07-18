from .skill_spec_loader import SkillSpecLoader
from .llm_evaluator import LlmEvaluator
from .test_case_writer import TestCaseWriter

class SkillExecutor:
    """指定されたスキルのSKILL.md仕様書を基に、仕様の静的チェックを行い、合格した場合はインテント評価用のテストケースを自動生成してファイルに書き出すワークフロー。"""
    def __init__(self):
        pass

    def generate_trigger_tests(self, skill_name: str, output_path: str) -> bool:
        """指定されたスキルのSKILL.md仕様書を基に、仕様の静的チェックを行い、合格した場合はインテント評価用のテストケースを自動生成してファイルに書き出すワークフローを実行します。

        Args:
            skill_name: テストケースを生成する対象スキルの名前。
            output_path: 生成されたテストケースを保存するファイルのパス（TrajectoryEvalSetフォーマットのJSON）。

        Returns:
            成功した場合は True、失敗した場合は False。
        """
        try:
            # 1. SKILL.mdをロード
            skill_spec_loader = SkillSpecLoader(skill_name)
            skill_spec_content = skill_spec_loader.load_skill_md()

            # 2. LLMで仕様の明確性を評価
            llm_evaluator = LlmEvaluator(skill_name)
            is_clarity_ok = llm_evaluator.evaluate_skill_clarity(skill_spec_content)

            if not is_clarity_ok:
                print(f"スキル '{skill_name}' のSKILL.md仕様は明確性チェックに不合格でした。")
                return False

            print(f"スキル '{skill_name}' のSKILL.md仕様は明確性チェックに合格しました。テストケースの生成を開始します。")

            # 3. LLMでインテント評価用テストケースを生成
            test_cases = llm_evaluator.generate_test_cases(skill_spec_content)

            # 4. 生成されたテストケースをファイルに書き出し
            test_case_writer = TestCaseWriter()
            test_case_writer.write_eval_case_set(output_path, test_cases)

            print(f"トリガーテストケースを '{output_path}' に正常に生成・保存しました。")
            return True

        except FileNotFoundError as e:
            import traceback; traceback.print_exc()
            print(f"エラー: {e}")
            return False
        except ValueError as e:
            import traceback; traceback.print_exc()
            print(f"エラー: {e}")
            return False
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"予期せぬエラーが発生しました: {e}")
            return False
