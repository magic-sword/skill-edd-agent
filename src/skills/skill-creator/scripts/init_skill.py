#!/usr/bin/env python3
"""
Skill Initializer CLI Wrapper (Thin Convention-Based Client)

Anthropic / Google ADK 2.0 準拠のスキル雛形生成を edd 統合 CLI に委譲します。
外部ライブラリへの直接 import 依存を持たず、プロセス境界（CLI-as-an-API）で動作します。

Usage:
    init_skill.py <skill-name> [--path <path>] [--pattern {workflow,task_based,reference,capabilities}]
"""

import sys
import subprocess
from pathlib import Path


def get_edd_cmd() -> list[str]:
    """edd コマンドの実行形式を解決します。"""
    try:
        res = subprocess.run(["edd", "--version"], capture_output=True, text=True)
        if res.returncode == 0:
            return ["edd"]
    except Exception:
        pass
    return [sys.executable, "-m", "edd_agent_tools.cli"]


def main():
    base_cmd = get_edd_cmd()
    cmd = base_cmd + ["init"] + sys.argv[1:]
    res = subprocess.run(cmd)
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
