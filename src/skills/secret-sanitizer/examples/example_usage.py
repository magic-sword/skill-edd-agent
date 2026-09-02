#!/usr/bin/env python3
"""
Example usage demonstrations for secret-sanitizer skill.
"""

import subprocess
import sys
from pathlib import Path


def demonstrate_cli_invocations():
    script_path = Path(__file__).parent.parent / "scripts" / "secret_sanitizer.py"

    # Example 1: Sanitize API Key & Password in string
    sample_text = "Connect to db with password: MySecretPassword123 and api_key: ak_test_1234567890abcdef"
    print("--- Example 1: Sanitize API Key & Password ---")
    res = subprocess.run(
        [sys.executable, str(script_path), "--input", sample_text],
        capture_output=True,
        text=True
    )
    print(res.stdout)

    # Example 2: Target specific secret types only (e.g., email only)
    sample_mixed = "Contact user@example.com or check host 192.168.1.1"
    print("--- Example 2: Filter by specific type (email only) ---")
    res2 = subprocess.run(
        [sys.executable, str(script_path), "--input", sample_mixed, "--types", "email"],
        capture_output=True,
        text=True
    )
    print(res2.stdout)


if __name__ == "__main__":
    demonstrate_cli_invocations()
