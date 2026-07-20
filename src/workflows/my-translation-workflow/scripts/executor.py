from typing import Literal

from .models import (
    TranslateToEnglishOutput,
    ToUppercaseTextOutput,
    CountCharactersOutput,
    ProcessTextOutput,
)

class SkillExecutor:
    """入力文字列を英語に翻訳し、大文字に変換した後、文字数をカウントするワークフロー機能。"""

    def __init__(self):
        # 必要な初期化処理をここに記述します
        pass

    def translate_to_english(self, text: str, source_lang: str) -> TranslateToEnglishOutput:
        """指定された文字列を英語に翻訳します。"""
        # ここでは簡易的に翻訳をシミュレートします。
        # 実際には外部の翻訳APIを呼び出すことになります。
        if source_lang == "en":
            translated_text = text
        else:
            # 例: 日本語から英語への簡易翻訳
            if text == "こんにちは":
                translated_text = "Hello"
            elif text == "ありがとう":
                translated_text = "Thank you"
            else:
                translated_text = f"Translated: {text}" # その他のテキストはプレフィックスを付けて返す
        
        return TranslateToEnglishOutput(translated_text=translated_text, status="success")

    def to_uppercase_text(self, text: str) -> ToUppercaseTextOutput:
        """指定された文字列をすべて大文字に変換します。"""
        uppercase_text = text.upper()
        return ToUppercaseTextOutput(uppercase_text=uppercase_text, status="success")

    def count_characters(self, text: str) -> CountCharactersOutput:
        """指定された文字列の文字数をカウントします。"""
        character_count = len(text)
        return CountCharactersOutput(character_count=character_count, status="success")

    def process_text(self, text: str, source_lang: str) -> ProcessTextOutput:
        """入力文字列を英語に翻訳し、大文字に変換した後、文字数をカウントするワークフロー機能。"""
        original_text = text

        # 1. 英語に翻訳
        translated_result = self.translate_to_english(text=original_text, source_lang=source_lang)
        if translated_result.status == "failed":
            return ProcessTextOutput(
                original_text=original_text,
                translated_text="",
                uppercase_text="",
                character_count=0,
                status="failed",
                message=f"翻訳に失敗しました: {original_text}"
            )
        translated_text = translated_result.translated_text

        # 2. 大文字に変換
        uppercase_result = self.to_uppercase_text(text=translated_text)
        if uppercase_result.status == "failed":
            return ProcessTextOutput(
                original_text=original_text,
                translated_text=translated_text,
                uppercase_text="",
                character_count=0,
                status="failed",
                message=f"大文字変換に失敗しました: {translated_text}"
            )
        uppercase_text = uppercase_result.uppercase_text

        # 3. 文字数をカウント
        count_result = self.count_characters(text=uppercase_text)
        if count_result.status == "failed":
            return ProcessTextOutput(
                original_text=original_text,
                translated_text=translated_text,
                uppercase_text=uppercase_text,
                character_count=0,
                status="failed",
                message=f"文字数カウントに失敗しました: {uppercase_text}"
            )
        character_count = count_result.character_count

        return ProcessTextOutput(
            original_text=original_text,
            translated_text=translated_text,
            uppercase_text=uppercase_text,
            character_count=character_count,
            status="success",
            message="テキスト処理が正常に完了しました。"
        )
