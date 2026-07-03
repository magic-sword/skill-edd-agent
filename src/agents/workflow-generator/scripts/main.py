"""
Unified entry point for workflow-generator.
"""
import argparse
import asyncio
import os
import sys
import json

# 動的インポートとロードの解決
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_workflow import generate_workflow_code, run_workflow_developer_agent

def main():
    parser = argparse.ArgumentParser(description="ADKサブエージェントを用いたワークフローの自律的生成と検証")
    parser.add_argument("--workflow_name", required=True, help="作成するワークフローエージェントの名前 (例: data-pipeline)")
    parser.add_argument("--prompt", required=True, help="生成したいワークフローの要件や手順")
    parser.add_argument("--output_dir", help="出力先 (例: src/agents/data-pipeline)")
    parser.add_argument("--model", default="gemini-2.5-flash", help="使用するモデル名")
    parser.add_argument("--max_attempts", type=int, default=15, help="サブエージェントの最大ターン数")
    parser.add_argument("--output_json", help="Path to output JSON file")
    
    args = parser.parse_args()
    
    if not os.environ.get("GEMINI_API_KEY"):
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。", file=sys.stderr)
        sys.exit(1)
        
    status = "success"
    message = "Successfully generated workflow."
    workflow_name = args.workflow_name
    
    if args.output_dir:
        output_dir = os.path.abspath(args.output_dir)
    else:
        output_dir = os.path.abspath(f"/workspace/src/agents/{workflow_name}")
    
    print(f"=== ワークフロー開発タスクを開始します ===")
    print(f"ワークフロー名: {workflow_name}")
    print(f"出力先: {output_dir}")
    print(f"要件: {args.prompt}")
    
    try:
        asyncio.run(
            run_workflow_developer_agent(
                output_dir=output_dir,
                workflow_name=workflow_name,
                prompt=args.prompt,
                model=args.model,
                max_turns=args.max_attempts
            )
        )
        print("\n=== ワークフロー開発タスクが完了しました ===")
    except Exception as e:
        status = "failed"
        message = str(e)
        print(f"Error: {e}", file=sys.stderr)
        
    if args.output_json:
        try:
            out_dir = os.path.dirname(os.path.abspath(args.output_json))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.output_json, "w", encoding="utf-8") as f:
                json.dump({
                    "status": status,
                    "message": message,
                    "output_dir": output_dir
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing output_json: {e}", file=sys.stderr)
            
    if status == "failed":
        sys.exit(1)

if __name__ == "__main__":
    main()
