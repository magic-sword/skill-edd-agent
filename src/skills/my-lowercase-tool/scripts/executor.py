from .models import SkillDeveloperOutput
from .utils import to_lowercase
import os

class SkillExecutor:
    """入力された文字列の英字をすべて小文字に変換する機能を提供します。"""
    def __init__(self):
        # 必要な初期化処理をここに記述します
        pass

    def convert_to_lowercase(self, text_to_convert: str) -> SkillDeveloperOutput:
        """入力された文字列の英字をすべて小文字に変換します。

        Args:
            text_to_convert: 小文字に変換する文字列。

        Returns:
            変換後の文字列と処理結果を含む出力オブジェクト (SkillDeveloperOutput)。
        """
        try:
            lowercased_text = to_lowercase(text_to_convert)
            # 現在の作業ディレクトリをoutput_dirとして使用
            current_dir = os.getcwd()
            return SkillDeveloperOutput(
                status='success',
                message=f"小文字変換が正常に完了しました: {lowercased_text}",
                output_dir=current_dir
            )
        except Exception as e:
            current_dir = os.getcwd() # エラー時もoutput_dirは必要
            return SkillDeveloperOutput(
                status='failed',
                message=f"小文字変換中にエラーが発生しました: {str(e)}",
                output_dir=current_dir
            )
