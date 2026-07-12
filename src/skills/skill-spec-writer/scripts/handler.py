from .models import Output
from .executor import SkillExecutor

def write_spec(
    design_path: str = None,
    skill: str = None,
    output_dir: str = None,
    source_code_dir: str = None,
    prompt: str = None
) -> dict:
    """既存のスキル設計情報（design.json）を基に、ADK 2.0に準拠したSKILL.md仕様書を自動生成します。

    Args:
        design_path: 読み込み対象の design.json のファイルパス。
        skill: 対象スキル名。
        output_dir: 生成された SKILL.md の出力先ディレクトリ。
        source_code_dir: スキャン対象のソースコードディレクトリ。
        prompt: 追加の設計指示（プロンプト）。

    Returns:
        生成結果（status, message, output_dir）を含む辞書。
    """
    executor = SkillExecutor(
        design_path=design_path,
        skill=skill,
        output_dir=output_dir,
        source_code_dir=source_code_dir,
        prompt=prompt
    )
    result = executor.execute()
    return result.model_dump()
