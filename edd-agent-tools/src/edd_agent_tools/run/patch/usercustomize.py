# google.adk 名前空間デッドロック防止のための先行インポート
try:
    from google.adk.tools import ToolContext
except ImportError:
    pass

# rouge-score などの多言語パッチ
try:
    import rouge_score.tokenizers as tokenizers
    from tokenizers import Tokenizer

    class HuggingFaceMultilingualTokenizer(tokenizers.Tokenizer):
        def __init__(self, *args, **kwargs):
            # bert-base-multilingual-cased トークナイザーをロード
            self.tokenizer = Tokenizer.from_pretrained("bert-base-multilingual-cased")
            
        def tokenize(self, text):
            if not text:
                return []
            # CLS と SEP を除外してトークンリストを返す
            tokens = self.tokenizer.encode(text).tokens
            return [t for t in tokens if t not in ('[CLS]', '[SEP]')]

    # トークナイザーの差し替え
    tokenizers.DefaultTokenizer = HuggingFaceMultilingualTokenizer
except Exception as e:
    # 差し替え失敗時は元のデフォルト挙動を維持する
    pass
