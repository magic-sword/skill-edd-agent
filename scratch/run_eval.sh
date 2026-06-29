#!/bin/bash
cd /workspace
.venv/bin/adk eval src tests/file_processor_eval_set.json --print_detailed_results > /workspace/scratch/eval_output.log 2>&1
