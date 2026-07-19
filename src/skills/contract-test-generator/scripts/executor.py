import json
from pathlib import Path
from .models import GenerateTestCasesOutput
from .design_json_reader import DesignJsonReader
from .test_case_generator import TestCaseGenerator
from .eval_case_set_writer import EvalCaseSetWriter

class SkillExecutor:
    """指定されたスキルのdesign.jsonに基づき、正常系および異常系の単体テストケースを自動生成し、EvalCaseSetフォーマットのJSONとしてファイルに書き出すスキル。"""
    def __init__(self):
        self._design_json_reader = DesignJsonReader()
        self._test_case_generator = TestCaseGenerator()
        self._eval_case_set_writer = EvalCaseSetWriter()

    def generate_test_cases(self, skill_name: str, output_path: str) -> GenerateTestCasesOutput:
        """指定されたスキルのdesign.jsonに基づき、正常系および異常系の単体テストケースを自動生成し、EvalCaseSetフォーマットのJSONとしてファイルに書き出します。

        Args:
            skill_name: テストケースを生成する対象スキルの名前。
            output_path: 生成されたテストケースを書き出すファイルのパス。

        Returns:
            実行結果オブジェクト (GenerateTestCasesOutput)。
        """
        try:
            # 1. design.json のパスを解決し、内容を読み込む
            design_json_path = self._design_json_reader.get_design_json_path(skill_name)
            if not design_json_path.exists():
                print(f"Error: design.json not found for skill '{skill_name}' at {design_json_path}")
                return GenerateTestCasesOutput(success=False)

            with open(design_json_path, 'r', encoding='utf-8') as f:
                design_json_content = f.read()

            # 2. design.json の内容をパースする
            design_json = self._design_json_reader.parse_design_json_content(design_json_content)
            if design_json is None:
                print(f"Error: Failed to parse design.json for skill '{skill_name}'")
                return GenerateTestCasesOutput(success=False)

            # 3. テストケースを生成する
            eval_case_set = self._test_case_generator.generate_test_cases(design_json)

            # 4. 生成されたテストケースをJSON文字列に変換する
            output_json_string = self._eval_case_set_writer.convert_to_json_string(eval_case_set)

            # 5. 結果をファイルに書き出す
            output_file_path = Path(output_path)
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(output_json_string)

            print(f"Test cases successfully generated and written to {output_file_path}")
            return GenerateTestCasesOutput(success=True)

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return GenerateTestCasesOutput(success=False)
