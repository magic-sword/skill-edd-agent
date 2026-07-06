import os
from collections.abc import Callable
from typing import Any

class GeminiRequest:
    """Gemini APIへの1回のリクエスト（プロンプトおよび添付ファイルコンテキスト）を組み立てて実行するクラス。

    メソッドチェーンに対応し、流れるような記述でリクエストを構築できます。

    Attributes:
        prompt: LLMに与える主要な指示テキスト（プロンプト）。
        parts: 添付ファイルやルールテキストを含め、Geminiに引き渡すコンテンツパーツのリスト。
    """
    def __init__(self, prompt: str, client=None, auto_attach_rules: bool = True):
        """GeminiRequest を初期化します。

        Args:
            prompt: LLMに与える主要な指示テキスト（プロンプト）。
            client: このリクエストを実行するために紐付ける GeminiClient インスタンス。
            auto_attach_rules: True の場合、ワークスペース固有ルール（.agents/AGENTS.md）
                およびホームディレクトリ配下のグローバルルール（AGENTS.md / GEMINI.md）を自動検出し、
                リクエスト添付としてアタッチします。
        """
        self.prompt = prompt
        self.parts = [prompt] if prompt else []
        self._client = client
        if auto_attach_rules:
            self._attach_system_rules()

    def add_dir(self, directory: str, ref_root: str | None = None, file_filter: Callable[[str], bool] | None = None) -> "GeminiRequest":
        """
        指定されたディレクトリ配下のファイルをスキャンし、
        file_filter によって許可されたファイルをそれぞれ独立したテキストパーツとして添付に追加します。
        """
        if not os.path.exists(directory):
            return self
            
        if not os.path.isdir(directory):
            if file_filter is None or file_filter(directory):
                self.add_file(directory, ref_root)
            return self

        target_files = []
        for root, dirs, files in os.walk(directory):
            for f in files:
                file_path = os.path.join(root, f)
                if file_filter is None or file_filter(file_path):
                    target_files.append(file_path)

        if not target_files:
            return self

        ref_root = ref_root or os.path.dirname(directory)
        for file_path in sorted(target_files):
            rel_path = os.path.relpath(file_path, ref_root)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.parts.append(f"# --- File: {rel_path} ---\n{content}")
            except Exception as e:
                print(f"Warning: Failed to load file {file_path} for Gemini attachment: {e}")
        return self

    def add_file(self, file_path: str, ref_root: str | None = None) -> "GeminiRequest":
        """単一のファイルを独立したテキストパーツとして添付に追加します。"""
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return self
            
        ref_root = ref_root or os.path.dirname(file_path)
        rel_path = os.path.relpath(file_path, ref_root)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.parts.append(f"# --- File: {rel_path} ---\n{content}")
        except Exception as e:
            print(f"Warning: Failed to load file {file_path} for Gemini attachment: {e}")
        return self

    def add_text(self, text: str) -> "GeminiRequest":
        """任意のテキストコンテンツをパーツとして追加します。"""
        if text:
            self.parts.append(text)
        return self

    def build(self) -> list[str]:
        """Gemini API に渡すための contents リストを返します。"""
        return self.parts

    def execute(self, config: Any = None, model: str | None = None, **kwargs: Any) -> Any:
        """このリクエストで組み立てられたコンテンツを使用して、紐づくクライアントから API を呼び出します。"""
        if not self._client:
            raise RuntimeError("Error: This GeminiRequest is not associated with a GeminiClient.")
        return self._client.generate_content(
            contents=self,
            config=config,
            model=model,
            **kwargs
        )

    def _attach_system_rules(self):
        """適用されるプロジェクトルールおよびグローバルルールを動的に検出し、自動添付します。"""
        # 1. プロジェクト固有ルール
        project_root = self._find_project_root()
        project_rule_path = os.path.join(project_root, ".agents", "AGENTS.md")
        if os.path.exists(project_rule_path):
            try:
                with open(project_rule_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    self.parts.append(f"# --- System Rule: Project Rule (.agents/AGENTS.md) ---\n{content}")
            except Exception as e:
                print(f"Warning: Failed to load project rule: {e}")

        # 2. グローバルルール (新仕様: config/AGENTS.md)
        global_rule_path = os.path.expanduser("~/.gemini/config/AGENTS.md")
        if os.path.exists(global_rule_path):
            try:
                with open(global_rule_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    self.parts.append(f"# --- System Rule: Global Rule (config/AGENTS.md) ---\n{content}")
            except Exception as e:
                print(f"Warning: Failed to load global rule (AGENTS.md): {e}")

        # 3. グローバルルール (旧仕様: GEMINI.md)
        old_global_rule_path = os.path.expanduser("~/.gemini/GEMINI.md")
        if os.path.exists(old_global_rule_path):
            try:
                with open(old_global_rule_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    self.parts.append(f"# --- System Rule: Global Rule (GEMINI.md) ---\n{content}")
            except Exception as e:
                print(f"Warning: Failed to load global rule (GEMINI.md): {e}")

    def _find_project_root(self) -> str:
        """カレントワーキングディレクトリから親階層へ遡り、プロジェクトルートディレクトリを探索します。

        Returns:
            特定されたプロジェクトルートディレクトリの絶対パス。
            見つからない場合はカレントディレクトリの絶対パス。
        """
        current = os.path.abspath(os.getcwd())
        while True:
            if (os.path.exists(os.path.join(current, ".git")) or
                os.path.exists(os.path.join(current, ".agents")) or
                os.path.exists(os.path.join(current, "pyproject.toml"))):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return os.path.abspath(os.getcwd())
