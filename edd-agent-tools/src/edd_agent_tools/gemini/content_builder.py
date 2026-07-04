import os
from collections.abc import Callable

class GeminiContentBuilder:
    """
    Gemini APIへ渡す contents (マルチパーツ・メッセージ) を構築・管理するクラス。
    ソースコード、アセット、ドキュメント等のファイルをプロンプトに直書きせず、
    独立したテキストパーツとして添付することで、コンテキスト汚染を防止します。
    """
    def __init__(self, prompt: str):
        self.prompt = prompt
        self.parts = [prompt]  # 最初のパーツはメインの指示プロンプト

    def add_dir(self, directory: str, ref_root: str | None = None, file_filter: Callable[[str], bool] | None = None) -> int:
        """
        指定されたディレクトリ配下のファイルをスキャンし、
        file_filter デリゲートによって許可されたファイルをそれぞれ独立したテキストパーツとして添付に追加します。
        
        返り値: 添付されたファイル数
        """
        if not os.path.exists(directory):
            return 0
            
        if not os.path.isdir(directory):
            # 単一ファイルの場合
            if file_filter is None or file_filter(directory):
                return 1 if self.add_file(directory, ref_root) else 0
            return 0

        target_files = []
        for root, dirs, files in os.walk(directory):
            for f in files:
                file_path = os.path.join(root, f)
                # フィルタ用デリゲート（存在する場合）を評価
                if file_filter is None or file_filter(file_path):
                    target_files.append(file_path)

        if not target_files:
            return 0

        ref_root = ref_root or os.path.dirname(directory)
        count = 0
        for file_path in sorted(target_files):
            rel_path = os.path.relpath(file_path, ref_root)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # 独立したテキストパーツとして追加
                self.parts.append(f"# --- File: {rel_path} ---\n{content}")
                count += 1
            except Exception as e:
                print(f"Warning: Failed to load file {file_path} for Gemini attachment: {e}")
        return count

    def add_file(self, file_path: str, ref_root: str | None = None) -> bool:
        """単一のファイルを独立したテキストパーツとして添付に追加します。"""
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return False
            
        ref_root = ref_root or os.path.dirname(file_path)
        rel_path = os.path.relpath(file_path, ref_root)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.parts.append(f"# --- File: {rel_path} ---\n{content}")
            return True
        except Exception as e:
            print(f"Warning: Failed to load file {file_path} for Gemini attachment: {e}")
            return False

    def build(self) -> list[str]:
        """Gemini API に渡すための contents リストを返します。"""
        return self.parts
