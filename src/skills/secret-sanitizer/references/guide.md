# Secret Sanitizer Specification & Pattern Guide

This reference document defines the detection patterns, mask placeholders, and edge case handling rules for `secret-sanitizer`.

---

## 1. Supported Secret Patterns

| Type | Identifier | Regex Trigger | Mask Format |
| :--- | :--- | :--- | :--- |
| **API Key / Token** | `api_key` | `(?:api[_-]?key\|apikey\|secret\|access[_-]?token)[\s:=]+["\']?([a-zA-Z0-9_\-]{16,64})` | `<API_KEY: ********>` |
| **Bearer Token** | `bearer_token` | `bearer\s+([a-zA-Z0-9_\-\.]{20,})` | `<BEARER_TOKEN: ********>` |
| **JWT Token** | `jwt` | `eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}` | `<JWT_TOKEN: ********>` |
| **Password** | `password` | `(?:password\|passwd\|pwd)[\s:=]+["\']?([^"\',\s\n]{4,64})` | `<PASSWORD: ********>` |
| **Email Address** | `email` | `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` | `<EMAIL: ********>` |
| **IPv4 Address** | `ipv4` | `\b(?:(?:25[0-5]\|2[0-4][0-9]\|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]\|2[0-4][0-9]\|[01]?[0-9][0-9]?)\b` | `<IP_ADDRESS: ********>` |

---

## 2. CLI Options & Syntax

- `--input`, `-i`: Raw text string to sanitize.
- `--file`, `-f`: Input file path to read from.
- `--output`, `-o`: Output file path to write sanitized result.
- `--types`, `-t`: Filter specific categories (e.g. `--types api_key jwt password`).
- `--mask-char`: Custom masking character (default: `*`).

---

## 3. Preservation of Non-Secret Context

- Whitespace, indentation, line breaks, punctuation, and surrounding code syntax (JSON, YAML, Python, Markdown) are preserved intact.
- Only the sensitive value itself is replaced with the structured mask placeholder.
