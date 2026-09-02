"""
Contract and Golden tests for secret-sanitizer CLI script.
"""

import sys
import json
import subprocess
from pathlib import Path


def test_cli_help():
    script_path = Path(__file__).parent.parent / "scripts" / "secret_sanitizer.py"
    assert script_path.exists(), f"Script {script_path} not found"
    res = subprocess.run([sys.executable, str(script_path), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "secret_sanitizer.py" in res.stdout or "usage" in res.stdout.lower()
    assert "--input" in res.stdout


def test_contract_sanitization_cases():
    script_path = Path(__file__).parent.parent / "scripts" / "secret_sanitizer.py"

    # 1. API key and email
    sample_text = "Config api_key: sk-1234567890abcdef1234 and email: test@example.com"
    res = subprocess.run(
        [sys.executable, str(script_path), "--input", sample_text],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert "<API_KEY: ********>" in res.stdout
    assert "<EMAIL: ********>" in res.stdout
    assert "sk-1234567890abcdef1234" not in res.stdout

    # 2. Password masking
    res2 = subprocess.run(
        [sys.executable, str(script_path), "--input", "Database password: mysecurepassword99"],
        capture_output=True,
        text=True
    )
    assert res2.returncode == 0
    assert "<PASSWORD: ********>" in res2.stdout
    assert "mysecurepassword99" not in res2.stdout


def test_golden_config_sanitization():
    script_path = Path(__file__).parent.parent / "scripts" / "secret_sanitizer.py"
    golden_file = Path(__file__).parent / "secret-sanitizer_golden.evalset.json"
    
    with open(golden_file, "r", encoding="utf-8") as f:
        golden_data = json.load(f)

    for case in golden_data["cases"]:
        input_text = case["input_text"]
        res = subprocess.run(
            [sys.executable, str(script_path), "--input", input_text],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0
        stdout = res.stdout

        # Verify all expected mask labels are present
        for label in case["expected_mask_labels"]:
            assert f"<{label}:" in stdout, f"Missing mask label {label} in output"

        # Verify raw sensitive values are not present
        for raw_val in case["forbidden_raw_values"]:
            assert raw_val not in stdout, f"Raw secret leaked: {raw_val}"
