from .models import Output
from .executor import SkillExecutor

def code_skill(
    prompt: str,
    skill: str = None,
    design_path: str = None,
    output_dir: str = None
) -> dict:
    """設計定義ファイル(design.json)と機能要件(prompt)に基づき、ADK 2.0規約およびオブジェクト指向設計に準拠したスキル実装コードを自動生成・更新します。

    Args:
        prompt: 今回の実装・改修要望。
        skill: 対象スキル名。
        design_path: 設計定義ファイルのパス。
        output_dir: コードの出力先ディレクトリ。

    Returns:
        生成されたファイルの一覧とステータスを含む辞書。
    """
    executor = SkillExecutor(
        prompt=prompt,
        skill=skill,
        design_path=design_path,
        output_dir=output_dir
    )
    result = executor.execute()
    return result.model_dump()
