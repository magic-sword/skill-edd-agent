import re
import argparse
import sys

def to_upper(text: str) -> str:
    """
    文字列をすべて大文字に変換します。

    Args:
        text (str): 変換する入力文字列。

    Returns:
        str: 大文字に変換された文字列。
    """
    return text.upper()

def to_lower(text: str) -> str:
    """
    文字列をすべて小文字に変換します。

    Args:
        text (str): 変換する入力文字列。

    Returns:
        str: 小文字に変換された文字列。
    """
    return text.lower()

def to_camel_case(text: str) -> str:
    """
    文字列をキャメルケースに変換します。
    例: "hello world" -> "helloWorld"
    例: "hello_world" -> "helloWorld"
    例: "HelloWorld" -> "helloWorld"

    Args:
        text (str): 変換する入力文字列。

    Returns:
        str: キャメルケースに変換された文字列。
    """
    # 非英数字（スペース、ハイフン、アンダースコアなど）をスペースに置換し、小文字に変換
    normalized_text = re.sub(r'[^a-zA-Z0-9]+', ' ', text).lower()
    words = normalized_text.split()

    if not words:
        return ""

    # 最初の単語はそのまま、それ以降の単語は先頭を大文字にする
    camel_case_words = [words[0]] + [word.capitalize() for word in words[1:]]
    return "".join(camel_case_words)

def to_snake_case(text: str) -> str:
    """
    文字列をスネークケースに変換します。
    例: "hello world" -> "hello_world"
    例: "helloWorld" -> "hello_world"
    例: "HelloWorld" -> "hello_world"
    例: "ALLCAPS" -> "allcaps"
    例: "MyAPIKey" -> "my_api_key"

    Args:
        text (str): 変換する入力文字列。

    Returns:
        str: スネークケースに変換された文字列。
    """
    # 1. ハイフンやスペースをアンダースコアに置換
    s = re.sub(r'[-\s]+', '_', text)

    # 2. キャメルケースをスネークケースに変換
    # 大文字の連続の後に小文字が続く場合 (例: APIKey -> API_Key)
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', s)
    # 小文字または数字の後に大文字が続く場合 (例: helloWorld -> hello_World)
    s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)

    # 3. 全体を小文字に変換
    s = s.lower()

    # 4. 連続するアンダースコアを単一に、先頭/末尾のアンダースコアを削除
    s = re.sub(r'_+', '_', s).strip('_')
    return s

def main():
    """
    コマンドライン引数から文字列と変換タイプを受け取り、変換結果を出力します。
    """
    parser = argparse.ArgumentParser(
        description="入力された文字列を指定されたケースに変換します。"
    )
    parser.add_argument(
        "text",
        type=str,
        help="変換する入力文字列。"
    )
    parser.add_argument(
        "type",
        type=str,
        choices=["upper", "lower", "camel", "snake"],
        help="変換タイプ (upper, lower, camel, snake)。"
    )

    args = parser.parse_args()

    converted_text: str
    if args.type == "upper":
        converted_text = to_upper(args.text)
    elif args.type == "lower":
        converted_text = to_lower(args.text)
    elif args.type == "camel":
        converted_text = to_camel_case(args.text)
    elif args.type == "snake":
        converted_text = to_snake_case(args.text)
    else:
        # このパスはargparseのchoicesによって到達しないはずですが、念のため
        print(f"エラー: 未知の変換タイプ '{args.type}'", file=sys.stderr)
        sys.exit(1)

    print(converted_text)

if __name__ == "__main__":
    main()