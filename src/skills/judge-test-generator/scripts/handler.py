from .executor import SkillExecutor

def generate_tests(skill_name: str, output_path: str) -> bool:
    """design.jsonおよびSKILL.mdをインプットとして、ルーブリック評価セットをLLMで自動生成し、指定されたパスに書き出します。

    Args:
        skill_name: ルーブリックテストを生成する対象スキルの名前。
        output_path: 生成されたテストファイルを書き出す絶対パス。

    Returns:
        成功すれば True, 失敗すれば False。
    """
    executor = SkillExecutor()
    return executor.generate_tests(skill_name=skill_name, output_path=output_path)
