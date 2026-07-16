from .models import GenerateSkillSpecOutput
from .executor import SkillExecutor

def generate_skill_spec(design_path: str | None = None, skill: str | None = None, output_dir: str | None = None, source_code_dir: str | None = None, prompt: str | None = None) -> GenerateSkillSpecOutput:
    """既存のスキル設計情報（design.json）を基に、ADK 2.0に準拠したSKILL.md仕様書を自動生成します。

    Args:
        design_path: design.json ファイルの直接のパス。省略された場合は skill から自動探索します。
        skill: 対象の既存スキル名。design_path 省略時の自動探索キーとして使用されます。
        output_dir: 生成されたSKILL.mdを保存するディレクトリのパス。省略時は対象スキルのディレクトリに出力されます。
        source_code_dir: 実装ソースコードが格納されたディレクトリパス（または単一ファイル）。指定しない場合、自動的にスキルの scripts ディレクトリを探索します。
        prompt: 仕様書生成における、特別に明記したい追加の表現上のこだわりや注意点などの指示。

    Returns:
        実行結果オブジェクト (GenerateSkillSpecOutput)。
    """
    executor = SkillExecutor()
    return executor.generate_skill_spec(design_path=design_path, skill=skill, output_dir=output_dir, source_code_dir=source_code_dir, prompt=prompt)
