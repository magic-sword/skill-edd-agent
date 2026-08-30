#!/usr/bin/env python3
"""
Case Converter - 決定論的テキストケース変換 CLI ツール (Zero-Dependency)

文字列やファイルを camelCase, snake_case, PascalCase, kebab-case, CONSTANT_CASE,
Title Case, lower, upper に相互変換します。
外部ライブラリ非依存（標準ライブラリのみ）で動作します。

Usage:
    python case_converter.py <text> --to <target_case>
    python case_converter.py --input <text> --format <target_case>
    cat input.txt | python case_converter.py --to snake
"""

import sys
import re
import argparse
from typing import List


def split_words(text: str) -> List[str]:
    """任意の文字列を単語（トークン）のリストに分割します。"""
    # 記号（ハイフン、アンダースコア、空白等）で分割
    clean = re.sub(r'[\-_.\s]+', ' ', text)
    # キャメルケースやパスカルケースの単語境界を分割（例: 'fooBar' -> 'foo Bar', 'HTMLParser' -> 'HTML Parser'）
    clean = re.sub(r'([a-z\d])([A-Z])', r'\1 \2', clean)
    clean = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', clean)
    words = [w.strip() for w in clean.split() if w.strip()]
    return words


def convert_case(text: str, target_case: str) -> str:
    """指定されたケース形式に文字列を変換します。"""
    target = target_case.lower().replace("-", "_")
    words = split_words(text)
    if not words:
        return ""

    if target in ("camel", "camel_case", "camelcase"):
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])
    elif target in ("snake", "snake_case", "snakecase"):
        return "_".join(w.lower() for w in words)
    elif target in ("pascal", "pascal_case", "pascalcase"):
        return "".join(w.capitalize() for w in words)
    elif target in ("kebab", "kebab_case", "kebabcase", "hyphen"):
        return "-".join(w.lower() for w in words)
    elif target in ("constant", "constant_case", "upper_snake"):
        return "_".join(w.upper() for w in words)
    elif target in ("title", "title_case", "titlecase"):
        return " ".join(w.capitalize() for w in words)
    elif target in ("upper", "uppercase"):
        return text.upper()
    elif target in ("lower", "lowercase"):
        return text.lower()
    else:
        raise ValueError(f"Unsupported target case format: '{target_case}'")


def parse_args():
    parser = argparse.ArgumentParser(
        prog="case_converter.py",
        description="Deterministic text case conversion tool (camelCase, snake_case, PascalCase, kebab-case, etc.)"
    )
    parser.add_argument("text", nargs="?", default=None, help="Input text string to convert")
    parser.add_argument("--input", "-i", dest="input_text", help="Alternative way to provide input text")
    parser.add_argument("--to", "-t", "--format", "-f", dest="target_case", default="snake",
                        help="Target case format (camel, snake, pascal, kebab, constant, title, upper, lower). Default: snake")
    parser.add_argument("--file", help="Path to input text file")
    parser.add_argument("--output", "-o", help="Path to output file (default: stdout)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_content = None
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                input_content = f.read()
        except Exception as e:
            print(f"Error reading file '{args.file}': {e}", file=sys.stderr)
            return 1
    elif args.text is not None:
        input_content = args.text
    elif args.input_text is not None:
        input_content = args.input_text
    elif not sys.stdin.isatty():
        input_content = sys.stdin.read()

    if input_content is None:
        print("Error: No input text provided. Pass text as argument or via stdin.", file=sys.stderr)
        return 1

    try:
        # 複数行の場合は行ごとに変換
        lines = input_content.splitlines()
        converted_lines = [convert_case(line, args.target_case) if line.strip() else "" for line in lines]
        result = "\n".join(converted_lines)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result + "\n")
        else:
            print(result)
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
