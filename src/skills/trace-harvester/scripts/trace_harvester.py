#!/usr/bin/env python3
"""
Trace Harvester Helper Script for trace-harvester skill
"""

import sys
import argparse
from pathlib import Path
from edd_agent_tools.meta.trace_harvester import TraceHarvester


def main():
    parser = argparse.ArgumentParser(description="Harvest skill scaffold from execution traces")
    parser.add_argument("trace_file", help="Path to execution trace JSON file")
    parser.add_argument("skill_name", help="Name of the skill to generate")
    parser.add_argument("--out", "-o", default="src/skills", help="Output base directory (default: src/skills)")
    parser.add_argument("--pattern", default="task_based", help="Skill pattern template")

    args = parser.parse_args()

    trace_path = Path(args.trace_file).resolve()
    if not trace_path.exists():
        print(f"Error: Trace file '{trace_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    import json
    with open(trace_path, "r", encoding="utf-8") as f:
        trace_data = json.load(f)

    harvester = TraceHarvester()
    res = harvester.harvest_skill_from_trace(
        trace_data=trace_data,
        suggested_skill_name=args.skill_name,
        output_base_dir=args.out,
        pattern=args.pattern
    )
    print(f"✅ Successfully harvested skill '{args.skill_name}': {res.get('skill_dir')}")


if __name__ == "__main__":
    main()
