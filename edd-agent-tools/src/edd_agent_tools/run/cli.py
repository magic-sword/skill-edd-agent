"""
Unified CLI runner for executing agent skills dynamically based on their handler schema.
"""
import sys
import os
import json
import inspect
from typing import Dict, Any, Callable

# 多言語パッチ（モンキーパッチ）の強制インプロセス適用
try:
    import edd_agent_tools.run.patch.usercustomize
except ImportError:
    pass

# Ensure edd-agent-tools is in path if executed directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from google.adk.tools import ToolContext
from edd_agent_tools.run.mock_context import MockInvocationContext
from edd_agent_tools.run.loader import SkillLoader
from edd_agent_tools.run.cli_parser import FunctionArgumentParser

class SkillRunner:
    """
    動的にロードされたスキル内の関数を実行し、ToolContext および Workspace環境 のセットアップと結果の出力を管理するランナー。
    """
    def __init__(
        self, 
        skill_name: str, 
        functions: Dict[str, Callable],
        env_type: str = "sandbox",
        workspace_dir: str = ".",
        apply_on_success: bool = False
    ):
        self.skill_name = skill_name
        self.functions = functions
        self.env_type = env_type
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.apply_on_success = apply_on_success

    def run(self):
        # 1. 実行対象関数の決定
        # 位置引数として関数名が指定されているか確認する
        args = sys.argv[2:]
        func_name = None
        
        if len(self.functions) == 1:
            # 公開関数が1つだけの場合は、関数名を省略可能とする
            func_name = list(self.functions.keys())[0]
            # もし最初の引数がその関数名であれば消費する
            if args and args[0] == func_name:
                args = args[1:]
        else:
            # 複数ある場合は、最初の位置引数を関数名として強制
            if not args or args[0].startswith("-"):
                func_list = ", ".join(self.functions.keys())
                print(f"Error: Multiple functions found in '{self.skill_name}'. You must specify which function to run as the first argument.", file=sys.stderr)
                print(f"Available functions: {func_list}", file=sys.stderr)
                sys.exit(1)
            func_name = args[0]
            if func_name not in self.functions:
                func_list = ", ".join(self.functions.keys())
                print(f"Error: Function '{func_name}' not found in '{self.skill_name}'.", file=sys.stderr)
                print(f"Available functions: {func_list}", file=sys.stderr)
                sys.exit(1)
            args = args[1:]

        target_func = self.functions[func_name]
        
        # 2. パーサーの構築と引数のパース・検証
        parser = FunctionArgumentParser(target_func, f"CLI runner for {self.skill_name}.{func_name}")
        try:
            validated_args, parsed_args = parser.parse_args(args)
        except Exception as e:
            print(f"Validation Error: {e}", file=sys.stderr)
            sys.exit(1)

        # 3. ToolContext のインジェクション判定とバインド
        sig = inspect.signature(target_func)
        context_param_name = None
        for name, param in sig.parameters.items():
            if name in ("context", "tool_context") or "ToolContext" in str(param.annotation):
                context_param_name = name
                break

        if context_param_name:
            tool_context = ToolContext(invocation_context=MockInvocationContext())
            validated_args[context_param_name] = tool_context
        else:
            tool_context = None

        # 3-2. env (WorkspaceEnvProtocol) のインジェクション判定とバインド
        env_param_name = None
        for name, param in sig.parameters.items():
            if name in ("env", "environment") or "WorkspaceEnvProtocol" in str(param.annotation):
                env_param_name = name
                break

        env_instance = None
        if env_param_name:
            from edd_agent_tools.evaluation import LocalWorkspaceEnv, RealWorkspaceEnv
            if self.env_type == "real":
                env_instance = RealWorkspaceEnv(workspace_dir=self.workspace_dir)
            else:
                env_instance = LocalWorkspaceEnv(workspace_dir=self.workspace_dir)
            
            # 環境の初期化
            env_instance.reset()
            validated_args[env_param_name] = env_instance

        # 4. 関数の実行と例外クリーンアップ
        result = None
        execution_success = False
        try:
            result = target_func(**validated_args)
            execution_success = True
        except Exception as e:
            print(f"Error executing function '{func_name}': {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            if env_instance:
                # sandbox 実行で成功した場合に自動永続化
                if self.env_type == "sandbox" and self.apply_on_success and execution_success:
                    try:
                        from edd_agent_tools.evaluation import LocalFileApplier
                        artifacts = env_instance.export_artifacts()
                        if artifacts.modified_files or artifacts.deleted_files:
                            print(f"[CLI] Applying sandbox artifacts to production directory '{self.workspace_dir}'...", file=sys.stderr)
                            applier = LocalFileApplier(target_dir=self.workspace_dir)
                            applier.apply(artifacts)
                        else:
                            print("[CLI] No changes detected in sandbox. Skipping apply.", file=sys.stderr)
                    except Exception as e:
                        print(f"[CLI] Error applying sandbox artifacts: {e}", file=sys.stderr)
                env_instance.close()

        # 5. 結果のシリアライズと出力
        if result is None and tool_context:
            result_data = tool_context.state.to_dict() if hasattr(tool_context.state, "to_dict") else dict(tool_context.state)
        else:
            result_data = result

        if hasattr(result_data, "model_dump"):
            result_data = result_data.model_dump()
        elif hasattr(result_data, "dict"):
            result_data = result_data.dict()

        result_json = json.dumps(result_data, ensure_ascii=False, indent=2)
        print(result_json)

        if parsed_args.output_json:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(parsed_args.output_json)), exist_ok=True)
                with open(parsed_args.output_json, 'w', encoding='utf-8') as f:
                    f.write(result_json)
            except Exception as e:
                print(f"Error writing to output_json: {e}", file=sys.stderr)
                sys.exit(1)

def run_cli():
    args = sys.argv[1:]
    min_tier_val = None
    env_type = "sandbox"
    workspace_dir = os.getcwd()
    apply_on_success = False
    
    filtered_args = []
    i = 0
    while i < len(args):
        if args[i] in ("--min-tier", "--min_tier"):
            if i + 1 < len(args):
                try:
                    min_tier_val = int(args[i+1])
                except ValueError:
                    from edd_agent_tools.skills.models import SkillTier
                    try:
                        min_tier_val = SkillTier[args[i+1].upper()]
                    except KeyError:
                        print(f"Error: Invalid --min-tier value: {args[i+1]}", file=sys.stderr)
                        sys.exit(1)
                i += 2
                continue
        elif args[i] in ("--env", "-e"):
            if i + 1 < len(args):
                env_type = args[i+1].lower()
                if env_type not in ("sandbox", "real"):
                    print(f"Error: Invalid --env value: {args[i+1]}. Must be 'sandbox' or 'real'.", file=sys.stderr)
                    sys.exit(1)
            i += 2
            continue
        elif args[i] in ("--workspace-dir", "--workspace_dir", "-w"):
            if i + 1 < len(args):
                workspace_dir = args[i+1]
            i += 2
            continue
        elif args[i] == "--apply":
            apply_on_success = True
            i += 1
            continue

        filtered_args.append(args[i])
        i += 1

    if not filtered_args or filtered_args[0].startswith("-"):
        print("Error: Skill name is required as the first argument.", file=sys.stderr)
        print("Usage: python3 -m edd_agent_tools.run [--min-tier <val>] [--env <sandbox|real>] [--workspace-dir <path>] [--apply] <skill_name> [function_name] [options]", file=sys.stderr)
        sys.exit(1)

    skill_name = filtered_args[0]
    sys.argv = [sys.argv[0], skill_name] + filtered_args[1:]

    # 【最新設定の同期と skills.json の出力（自動同期）】
    try:
        from edd_agent_tools.state import SkillsState
        from edd_agent_tools.models.state import SkillTier
        state = SkillsState()
        state.load()
        
        filter_tier = None
        if min_tier_val is not None:
            filter_tier = SkillTier(min_tier_val)
            
        state.save(filter_tier=filter_tier)
    except Exception as e:
        print(f"Warning: Failed to sync and generate skills.json: {e}", file=sys.stderr)

    # スキルモジュールのロード
    try:
        loader = SkillLoader(skill_name)
        functions = loader.load()
    except Exception as e:
        print(f"Error loading skill module '{skill_name}': {e}", file=sys.stderr)
        sys.exit(1)

    runner = SkillRunner(
        skill_name, 
        functions, 
        env_type=env_type, 
        workspace_dir=workspace_dir, 
        apply_on_success=apply_on_success
    )
    runner.run()

if __name__ == "__main__":
    run_cli()
