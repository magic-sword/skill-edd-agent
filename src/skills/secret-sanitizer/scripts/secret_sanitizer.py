#!/usr/bin/env python3
"""
Secret Sanitizer CLI Tool.
Detects and masks sensitive information (API keys, JWT tokens, passwords, emails, IP addresses) in text and files.
Zero-dependency implementation using Python standard library.
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Dict, Pattern, List, Tuple


# Regex patterns for common secrets
PATTERNS: Dict[str, Tuple[Pattern[str], str]] = {
    "api_key": (
        re.compile(r'(?i)(?:api[_-]?key|apikey|secret|access[_-]?token|auth[_-]?token)(?:\s+is|\s*[:=])\s*["\']?([a-zA-Z0-9_\-]{16,64})["\']?'),
        "API_KEY"
    ),
    "bearer_token": (
        re.compile(r'(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})'),
        "BEARER_TOKEN"
    ),
    "jwt": (
        re.compile(r'eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}'),
        "JWT_TOKEN"
    ),
    "password": (
        re.compile(r'(?i)(?:password|passwd|pwd)(?:\s+is|\s*[:=])\s*["\']?([^"\',\s\n]{4,64})["\']?'),
        "PASSWORD"
    ),
    "email": (
        re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),
        "EMAIL"
    ),
    "ipv4": (
        re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
        "IP_ADDRESS"
    ),
}


def sanitize_text(text: str, mask_char: str = "*", selected_types: List[str] = None) -> Tuple[str, int]:
    """Sanitizes text by replacing secrets with masked placeholders."""
    count = 0
    result = text
    
    types_to_check = selected_types if selected_types else list(PATTERNS.keys())
    
    for secret_type in types_to_check:
        if secret_type not in PATTERNS:
            continue
        pattern, label = PATTERNS[secret_type]
        
        # Special handling for capture groups vs full match
        def replace_fn(match: re.Match) -> str:
            nonlocal count
            count += 1
            full_match = match.group(0)
            if match.groups():
                # Replace only the captured sensitive group
                captured = match.group(1)
                replacement = f"<{label}: {mask_char * 8}>"
                return full_match.replace(captured, replacement, 1)
            else:
                return f"<{label}: {mask_char * 8}>"

        result = pattern.sub(replace_fn, result)
        
    return result, count


def main():
    parser = argparse.ArgumentParser(
        description="Sanitize sensitive secrets (API keys, passwords, JWTs, emails, IPs) from text or files."
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input text string to sanitize."
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Path to input text file to sanitize."
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Optional path to write sanitized output file."
    )
    parser.add_argument(
        "--types", "-t",
        nargs="+",
        choices=["api_key", "bearer_token", "jwt", "password", "email", "ipv4"],
        help="Specific secret types to sanitize (default: all)."
    )
    parser.add_argument(
        "--mask-char",
        type=str,
        default="*",
        help="Character to use for masking (default: '*')."
    )

    args = parser.parse_args()

    if not args.input and not args.file:
        parser.print_help()
        sys.exit(1)

    content = ""
    if args.input:
        content = args.input
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        content = file_path.read_text(encoding="utf-8")

    sanitized, count = sanitize_text(
        text=content,
        mask_char=args.mask_char,
        selected_types=args.types
    )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(sanitized, encoding="utf-8")
        print(f"Sanitized content written to {args.output} (Masked {count} sensitive item(s))")
    else:
        print(sanitized)


if __name__ == "__main__":
    main()
