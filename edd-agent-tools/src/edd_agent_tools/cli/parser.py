import argparse
import json
from typing import Type, Dict, Any, List, Tuple
from pydantic import BaseModel
from typing import get_origin, get_args, Union

class SchemaArgumentParser:
    """
    Pydanticモデル（InputSchema）から、argparse のオプション引数を動的に構築・パースし、
    入力値の検証および型への復元を行うパーサー。
    """
    def __init__(self, InputSchema: Type[BaseModel], description: str = ""):
        self.InputSchema = InputSchema
        self.description = description
        self.parser = argparse.ArgumentParser(
            description=description,
            formatter_class=argparse.RawTextHelpFormatter
        )
        self._build_parser()

    def _build_parser(self):
        # 共通引数の登録
        self.parser.add_argument("--skill_name", required=True, help="Name of the skill to run")
        self.parser.add_argument("--output_json", help="Path to save the output JSON data")

        # Pydanticモデルから動的に引数を登録
        for field_name, field_info in self.InputSchema.model_fields.items():
            opt_name = f"--{field_name}"
            field_type = field_info.annotation

            # Union（Optional）型から基本型をアンラップ
            origin = get_origin(field_type)
            if origin is Union:
                args_types = [a for a in get_args(field_type) if a is not type(None)]
                if args_types:
                    field_type = args_types[0]

            origin_type = get_origin(field_type) or field_type
            if origin_type in (int, float, bool, str):
                parser_type = origin_type
            else:
                parser_type = str  # list, dict等のコンテナ型は一旦文字列として受け取る

            required = field_info.is_required()
            default = field_info.default if not required else None

            help_text = field_info.description or ""
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

    def parse_and_validate(self, args_list: List[str]) -> Tuple[BaseModel, argparse.Namespace]:
        """
        引数をパースし、Pydanticのモデルクラスによるバリデーションを実施したインスタンスを返します。
        """
        parsed_args = self.parser.parse_args(args_list)

        raw_params = {}
        for field_name, field_info in self.InputSchema.model_fields.items():
            val = getattr(parsed_args, field_name)
            if val is not None:
                field_type = field_info.annotation
                origin = get_origin(field_type) or field_type
                # リストや辞書などのコンテナ型に文字列が渡されていた場合、JSONパースを試みる
                if isinstance(val, str) and origin in (list, dict, set, tuple):
                    try:
                        val = json.loads(val)
                    except Exception:
                        pass
                raw_params[field_name] = val

        # バリデーションの実行
        validated_input = self.InputSchema.model_validate(raw_params)
        return validated_input, parsed_args
