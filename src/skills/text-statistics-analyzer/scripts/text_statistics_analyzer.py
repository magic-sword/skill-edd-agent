#!/usr/bin/env python3
"""
Text Statistics Analyzer - 決定論的テキスト統計解析エンジン

テキストまたはファイルを入力として受け取り、文字数、単語数、文数、段落数、
推定読了時間を決定論的に算出し、Markdown または JSON 形式で出力します。
"""

import argparse
import collections
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def is_cjk(char: str) -> bool:
    """文字が CJK (日本語・中国語・韓国語文字) かどうかを判定する。"""
    code = ord(char)
    return (
        0x3040 <= code <= 0x309F or  # 平仮名
        0x30A0 <= code <= 0x30FF or  # 片仮名
        0x4E00 <= code <= 0x9FFF or  # CJK統合漢字
        0x3400 <= code <= 0x4DBF or  # CJK統合漢字拡張A
        0xF900 <= code <= 0xFAFF     # CJK互換漢字
    )


def analyze_text(
    text: str,
    wpm: int = 200,
    cpm: int = 500,
) -> Dict[str, Any]:
    """テキストを多角的に解析し、内部統計データモデルを生成する。"""
    if not text:
        return {
            "characters_total": 0,
            "characters_no_spaces": 0,
            "words": 0,
            "sentences": 0,
            "lines": 0,
            "paragraphs": 0,
            "reading_time_minutes": 0.0,
            "reading_time_formatted": "< 1 min",
            "top_words": [],
        }

    # 1. 文字数計算
    characters_total = len(text)
    characters_no_spaces = len(re.sub(r"\s+", "", text))

    # 2. 行数と段落数
    raw_lines = text.splitlines()
    lines_count = len(raw_lines)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    paragraphs_count = len(paragraphs) if paragraphs else (1 if text.strip() else 0)

    # 3. 文数計算 (。！？.!? などの終端記号で分割)
    sentence_delimiters = r"[。！？\.\!\?]+"
    raw_sentences = [s.strip() for s in re.split(sentence_delimiters, text) if s.strip()]
    sentences_count = len(raw_sentences) if raw_sentences else 1

    # 4. 単語数および言語比率の判定
    cjk_chars = [c for c in text if is_cjk(c)]
    cjk_count = len(cjk_chars)
    latin_words = re.findall(r"[A-Za-z0-9_\-]+", text)
    latin_count = len(latin_words)

    # 単語数は英単語数＋CJK文字（1文字=1単語相当の概算）
    total_words = latin_count + cjk_count

    # 5. 推定読了時間
    is_japanese = (characters_no_spaces > 0 and (cjk_count / max(1, characters_no_spaces)) > 0.3)
    if is_japanese:
        minutes = characters_no_spaces / max(1, cpm)
        reading_time_formatted = "< 1分" if minutes < 1.0 else f"~{math.ceil(minutes)}分"
    else:
        minutes = total_words / max(1, wpm)
        reading_time_formatted = "< 1 min" if minutes < 1.0 else f"~{math.ceil(minutes)} min"

    # 6. 頻出単語 (ストップワード除外)
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "on", "at",
        "to", "for", "with", "this", "that", "it", "of", "by", "from", "as",
        "これ", "それ", "あれ", "この", "その", "あの", "です", "ます", "である", "の", "に", "は", "を", "が",
    }
    tokens = [w.lower() for w in latin_words if len(w) > 2 and w.lower() not in stop_words]
    word_freq = collections.Counter(tokens)
    top_words = word_freq.most_common(5)

    return {
        "characters_total": characters_total,
        "characters_no_spaces": characters_no_spaces,
        "words": total_words,
        "sentences": sentences_count,
        "lines": lines_count,
        "paragraphs": paragraphs_count,
        "reading_time_minutes": round(minutes, 2),
        "reading_time_formatted": reading_time_formatted,
        "top_words": [{"word": w, "count": c} for w, c in top_words],
    }


def render_markdown(metrics: Dict[str, Any], is_japanese: bool = False) -> str:
    """解析結果を整形された Markdown 表としてレンダリングする。"""
    if is_japanese:
        output_lines = [
            "| 指標 | 値 |",
            "|---|---|",
            f"| 文字数（全体） | {metrics['characters_total']} |",
            f"| 文字数（空白除く） | {metrics['characters_no_spaces']} |",
            f"| 単語数（相当） | {metrics['words']} |",
            f"| 文数 | {metrics['sentences']} |",
            f"| 段落数 | {metrics['paragraphs']} |",
            f"| 推定読了時間 | {metrics['reading_time_formatted']} |",
        ]
    else:
        output_lines = [
            "| Metric | Value |",
            "|---|---|",
            f"| Characters (total) | {metrics['characters_total']} |",
            f"| Characters (no spaces) | {metrics['characters_no_spaces']} |",
            f"| Words | {metrics['words']} |",
            f"| Sentences | {metrics['sentences']} |",
            f"| Paragraphs | {metrics['paragraphs']} |",
            f"| Estimated Reading Time | {metrics['reading_time_formatted']} |",
        ]

    if metrics.get("top_words"):
        output_lines.append("")
        output_lines.append("### Frequent Terms")
        for item in metrics["top_words"]:
            output_lines.append(f"- **{item['word']}**: {item['count']}")

    return "\n".join(output_lines)


def main():
    parser = argparse.ArgumentParser(
        description="テキストの文字数、単語数、文数、読了時間を決定論的に解析する CLI ツール。"
    )
    parser.add_argument(
        "input_text",
        nargs="?",
        default=None,
        help="解析対象のテキスト文字列（位置引数）",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_opt",
        type=str,
        default=None,
        help="解析対象のテキストまたはファイルパス",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="出力フォーマット (markdown または json, デフォルト: markdown)",
    )
    parser.add_argument(
        "--wpm",
        type=int,
        default=200,
        help="英語想定の読了速度 (単語/分, デフォルト: 200)",
    )
    parser.add_argument(
        "--cpm",
        type=int,
        default=500,
        help="日本語想定の読了速度 (文字/分, デフォルト: 500)",
    )

    args = parser.parse_args()

    raw_input = args.input_opt or args.input_text
    if not raw_input:
        parser.print_help()
        return 1

    # ファイルパスの安全な判定（改行を含まず260文字以下の場合のみパスとして存在確認）
    content = raw_input
    if "\n" not in raw_input and len(raw_input) <= 260:
        try:
            input_path = Path(raw_input)
            if input_path.is_file():
                content = input_path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            pass

    metrics = analyze_text(content, wpm=args.wpm, cpm=args.cpm)

    # 言語判定 (CJK 文字が含まれるか)
    has_cjk = any(is_cjk(c) for c in content)

    if args.format == "json":
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(metrics, is_japanese=has_cjk))

    return 0


if __name__ == "__main__":
    sys.exit(main())
