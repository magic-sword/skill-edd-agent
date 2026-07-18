import os
from edd_agent_tools.skills import SkillsState
from .models import GenerateTestCasesOutput

class SkillExecutor:
    """指定されたスキルとテストタイプに基づき、対応するテスト生成スキルを動的にロードし、テストケースを生成するディスパッチャー。"""
    def __init__(self):
        self._skills_state = SkillsState()

    def generate_test_cases(self, skill: str, test_type: str) -> GenerateTestCasesOutput:
        """指定されたスキルとテストタイプに基づき、対応するテスト生成スキルを動的にロードし、テストケースを生成させます。

        Args:
            skill: テストケースを生成する対象のスキル名。
            test_type: 生成するテストケースの種別（例: 'trigger', 'unit'）。

        Returns:
            実行結果オブジェクト (GenerateTestCasesOutput)。
        """
        try:
            # 1. 対象スキルの取得とテスト保存先パスの解決
            target_skill = self._skills_state.get_skill(skill)
            tests_dir = os.path.join(target_skill.root_dir, "tests")
            os.makedirs(tests_dir, exist_ok=True)
            
            # ファイル名は [対象スキル名]_[test_type].evalset.json
            skill_name_underscore = skill.replace('-', '_')
            output_filename = f"{skill_name_underscore}_{test_type}.evalset.json"
            output_path = os.path.join(tests_dir, output_filename)

            # 2. 対応するテスト生成スキルを動的ロード
            # 例: test_type="trigger" -> "trigger-test-generator"
            generator_skill_name = f"{test_type}-test-generator"
            generator_skill = self._skills_state.get_skill(generator_skill_name)
            generator_module = generator_skill.load_module()

            # 3. 共通インターフェース関数の存在チェック
            if not hasattr(generator_module, "generate_tests"):
                return GenerateTestCasesOutput(
                    status="failed",
                    message=f"エラー: スキル '{generator_skill_name}' に 'generate_tests' 関数が定義されていません。",
                    eval_set_path=""
                )
            
            # 4. 生成実行
            # プロトコル: generate_tests(skill_name, output_path) -> bool
            success = generator_module.generate_tests(skill_name=skill, output_path=output_path)
            
            if success:
                return GenerateTestCasesOutput(
                    status="success",
                    message=f"テストケースを正常に生成し、'{output_path}' に保存しました。",
                    eval_set_path=output_path
                )
            else:
                return GenerateTestCasesOutput(
                    status="failed",
                    message=f"エラー: スキル '{generator_skill_name}' によるテストケースの生成に失敗しました。",
                    eval_set_path=""
                )

        except Exception as e:
            return GenerateTestCasesOutput(
                status="failed",
                message=f"予期せぬエラーが発生しました: {e}",
                eval_set_path=""
            )
