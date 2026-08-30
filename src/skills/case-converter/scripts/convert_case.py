import argparse

def to_upper_case(text: str) -> str:
    """
    文字列をすべて大文字に変換します。

    Args:
        text (str): 変換する文字列。

    Returns:
        str: 大文字に変換された文字列。
    """
    return text.upper()

def to_lower_case(text: str) -> str:
    """
    文字列をすべて小文字に変換します。

    Args:
        text (str): 変換する文字列。

    Returns:
        str: 小文字に変換された文字列。
    """
    return text.lower()

def to_camel_case(text: str) -> str:
    """
    文字列をキャメルケースに変換します。

    Args:
        text (str): 変換する文字列。

    Returns:
        str: キャメルケースに変換された文字列。
    """
    s = text.replace("_", " ").replace("-", " ")
    s = s.title().replace(" ", "")
    return s[0].lower() + s[1:] if s else ""

def to_snake_case(text: str) -> str:
    """
    文字列をスネークケースに変換します。

    Args:
        text (str): 変換する文字列。

    Returns:
        str: スネークケースに変換された文字列。
    """
    s = text.replace("-", "_")
    s = ''.join(['_' + c.lower() if c.isupper() else c for c in s])
    return s.lstrip('_').lower()

def main():
    """
    コマンドライン引数から文字列と変換ケースを受け取り、変換結果を出力します。
    """
    parser = argparse.ArgumentParser(
        description="入力された文字列を指定されたケース形式（upper, lower, camel, snake）に変換します。"
    )
    parser.add_argument(
        "text",
        type=str,
        help="変換する文字列。"
    )
    parser.add_argument(
        "case",
        type=str,
        choices=["upper", "lower", "camel", "snake"],
        help="変換するケース形式 (upper, lower, camel, snake)。"
    )

    args = parser.parse_args()

    converted_text = ""
    if args.case == "upper":
        converted_text = to_upper_case(args.text)
    elif args.case == "lower":
        converted_text = to_lower_case(args.text)
    elif args.case == "camel":
        converted_text = to_camel_case(args.text)
    elif args.case == "snake":
        converted_text = to_snake_case(args.text)
    
    print(converted_text)

if __name__ == "__main__":
    main()