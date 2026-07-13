import argparse
import json
import inspect
from typing import Type, Dict, Any, List, Tuple, Callable, get_origin, get_args, Union

class FunctionArgumentParser:
    """
    関数のシグネチャ（引数定義、型ヒント、デフォルト値）から argparse の引数を動的に構築し、
    入力値のパースと型変換を行うパーサー。
    """
    def __init__(self, func: Callable, description: str = ""):
        self.func = func
        self.description = description
        self.parser = argparse.ArgumentParser(
            description=description or func.__doc__,
            formatter_class=argparse.RawTextHelpFormatter
        )
        self.sig = inspect.signature(func)
        self.parameters = self.sig.parameters
        self._build_parser()

    def _build_parser(self):
        # 共通引数の登録
        self.parser.add_argument("--output_json", help="Path to save the output JSON data")

        # 関数のパラメータから引数を動的に登録
        for name, param in self.parameters.items():
            # ToolContext や WorkspaceEnvProtocol (または context, env などの引数) は CLI 引数から除外して自動注入対象とする
            if name in ("context", "tool_context", "env", "environment") or "ToolContext" in str(param.annotation) or "WorkspaceEnvProtocol" in str(param.annotation):
                continue
                
            opt_name = f"--{name}"
            param_type = param.annotation
            
            # Union（Optional）型から基本型をアンラップ
            origin = get_origin(param_type)
            if origin is Union:
                args_types = [a for a in get_args(param_type) if a is not type(None)]
                if args_types:
                    param_type = args_types[0]
                    
            origin_type = get_origin(param_type) or param_type
            
            # 型が不明または Any の場合は str にする
            if origin_type is inspect.Parameter.empty or origin_type is Any:
                parser_type = str
            elif origin_type in (int, float, bool, str):
                parser_type = origin_type
            else:
                parser_type = str  # list, dict等は一旦文字列で受け取って後でパース

            required = param.default is inspect.Parameter.empty
            default = param.default if not required else None

            # bool値の引数の型キャストヘルパー
            if parser_type is bool:
                def str2bool(v):
                    if isinstance(v, bool):
                        return v
                    if v.lower() in ('yes', 'true', 't', 'y', '1'):
                        return True
                    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
                        return False
                    else:
                        raise argparse.ArgumentTypeError('Boolean value expected.')
                parser_type = str2bool

            # ヘルプ文言の作成
            type_name = origin_type.__name__ if hasattr(origin_type, '__name__') else str(origin_type)
            help_text = f"Type: {type_name}"
            if required:
                help_text = f"(必須) {help_text}"
            elif default is not None:
                help_text = f"{help_text} (デフォルト: {default})"

            self.parser.add_argument(
                opt_name,
                type=parser_type,
                required=required,
                default=default,
                help=help_text
            )

    def parse_args(self, args_list: List[str]) -> Tuple[Dict[str, Any], argparse.Namespace]:
        """引数をパースし、型キャストされた辞書形式の引数を返します。"""
        parsed_args = self.parser.parse_args(args_list)
        
        args_dict = {}
        for name, param in self.parameters.items():
            if name in ("context", "tool_context", "env", "environment") or "ToolContext" in str(param.annotation) or "WorkspaceEnvProtocol" in str(param.annotation):
                continue
                
            val = getattr(parsed_args, name)
            if val is not None:
                param_type = param.annotation
                origin = get_origin(param_type) or param_type
                # コンテナ型（list, dict等）の場合、JSONとしてデコードしてみる
                if isinstance(val, str) and origin in (list, dict, set, tuple):
                    try:
                        val = json.loads(val)
                    except Exception:
                        pass
                args_dict[name] = val
                
        return args_dict, parsed_args
