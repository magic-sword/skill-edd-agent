"""
Contract tests for case-converter CLI script.
"""

import sys
import subprocess
from pathlib import Path


def test_cli_help():
    script_path = Path(__file__).parent.parent / "scripts" / "case_converter.py"
    assert script_path.exists(), f"Script {script_path} not found"
    res = subprocess.run([sys.executable, str(script_path), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "case_converter.py" in res.stdout or "usage" in res.stdout.lower()


def test_conversion_cases():
    script_path = Path(__file__).parent.parent / "scripts" / "case_converter.py"
    
    # 1. snake to camel
    res = subprocess.run([sys.executable, str(script_path), "hello_world_example", "--to", "camel"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "helloWorldExample" in res.stdout

    # 2. camel to snake
    res = subprocess.run([sys.executable, str(script_path), "helloWorldExample", "--to", "snake"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "hello_world_example" in res.stdout

    # 3. to kebab
    res = subprocess.run([sys.executable, str(script_path), "helloWorldExample", "--to", "kebab"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "hello-world-example" in res.stdout
