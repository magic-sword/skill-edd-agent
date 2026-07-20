from .executor import SkillExecutor

def generate_tests(skill_name: str, output_path: str) -> bool:
    """design.jsonおよびSKILL.mdをインプットとして、多様なユースケース入力値と、期待される正解のペアをLLMで自動生成し、指定されたパスに書き出します。

    Args:
        skill_name: ゴールデンテストを生成する対象スキルの名前。
        output_path: 生成されたゴールデンテストファイルを書き出す絶対パス。

    Returns:
        成功すれば True, 失敗すれば False。
    """
    executor = SkillExecutor()
    return executor.generate_tests(skill_name=skill_name, output_path=output_path)
