from .executor import SkillExecutor

def design_skill(
    prompt: str,
    summary: str = None,
    output_dir: str = None,
    skill: str = None,
    source_code_dir: str = None
) -> dict:
    """自然言語の要件や既存のソースコードを基に、ADK 2.0互換のdesign.jsonを設計・生成します。

    Args:
        prompt: 設計または再設計の要件（自然言語）。
        summary: 設計の概要（指示の上書き用）。
        output_dir: 生成された design.json の出力先ディレクトリ。
        skill: 対象スキル名（既存スキルの再設計時のみ）。
        source_code_dir: スキャン対象のソースコードディレクトリ（既存スキルの再設計時のみ）。

    Returns:
        設計結果（status, message, output_dir）を含む辞書。
    """
    executor = SkillExecutor(
        prompt=prompt,
        summary=summary,
        output_dir=output_dir,
        skill=skill,
        source_code_dir=source_code_dir
    )
    result = executor.execute()
    return result.model_dump()
