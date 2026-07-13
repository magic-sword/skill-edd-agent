from typing import Any, Union, Annotated
from pydantic import BaseModel, Field, create_model
from typing import get_origin, get_args

def _clean_type_annotation(anno: Any) -> Any:
    """型アノテーションを再帰的に解析し、内包される Pydantic モデルをクレンジング済みのモデルに置換します。"""
    if anno is None:
        return None

    # 直接 Pydantic モデルの場合 (例: Input)
    if isinstance(anno, type) and issubclass(anno, BaseModel):
        return clean_pydantic_schema(anno)

    # ジェネリック型 (例: list[BaseModel], Union[BaseModel, None] など) の場合
    origin = get_origin(anno)
    if origin is not None:
        args = get_args(anno)
        # 型引数をそれぞれ再帰的にクレンジング
        cleaned_args = tuple(_clean_type_annotation(arg) for arg in args)

        # Union の特殊な再構築
        if origin is Union:
            return Union[cleaned_args]

        try:
            # 引数の数に応じて型を再構成 (list[T] や dict[K, V] 等)
            if len(cleaned_args) == 1:
                return origin[cleaned_args[0]]
            else:
                return origin[cleaned_args]
        except Exception:
            return anno

    return anno

def clean_pydantic_schema(original_model: Any) -> Any:
    """Pydanticモデル定義（またはUnion型）から、Gemini APIが拒否するカスタムメタデータを除去したクローンモデルを返します（再帰適用）。"""
    if original_model is None:
        return None

    # Annotated型やUnion型の処理
    origin = get_origin(original_model)
    if origin is not None:
        args = get_args(original_model)
        cleaned_args = tuple(clean_pydantic_schema(arg) for arg in args)
        if origin is Union:
            # Union[A, B] などの再構築
            return Union[cleaned_args]
        elif origin is Annotated:
            # Annotated[Union[A, B], discriminator] などの再構築
            # GeminiAPI は Annotated メタデータを解釈できないことがあるため、ベースのUnion型を展開して再帰処理したものを返却する
            return cleaned_args[0]
        try:
            if len(cleaned_args) == 1:
                return origin[cleaned_args[0]]
            else:
                return origin[cleaned_args]
        except Exception:
            return original_model

    if not isinstance(original_model, type) or not issubclass(original_model, BaseModel):
        return original_model

    fields_definition = {}

    for field_name, field_info in original_model.model_fields.items():
        clean_extra = None
        if isinstance(field_info.json_schema_extra, dict):
            clean_extra = {
                k: v for k, v in field_info.json_schema_extra.items()
                if k not in ["is_prompt_parameter", "prompt_instructions", "prompt_constraints"]
            }

        cleaned_annotation = _clean_type_annotation(field_info.annotation)

        fields_definition[field_name] = (
            cleaned_annotation,
            Field(
                default=field_info.default,
                default_factory=field_info.default_factory,
                description=field_info.description,
                json_schema_extra=clean_extra
            )
        )

    return create_model(
        f"GeminiAPI_{original_model.__name__}",
        __config__={"extra": "ignore"},
        **fields_definition
    )

def PromptField(
    default=...,
    description: str = "",
    instructions: str = "",
    constraints: str = "",
    **kwargs
):
    """LLMへの直接の指示（プロンプト）として機能する特別なパラメータを定義するためのフィールドラッパー。

    Args:
        default: デフォルト値。
        description: パラメータの詳細説明。
        instructions: パラメータの有効な指定可能指示ガイドライン。
        constraints: パラメータの構造的な制約ガイドライン。
        **kwargs: 基礎となる Pydantic Field に引き渡す追加 of 属性。

    Returns:
        Pydantic の FieldInfo オブジェクト。
    """
    return Field(
        default,
        description=description,
        json_schema_extra={
            "is_prompt_parameter": True,
            "prompt_instructions": instructions,
            "prompt_constraints": constraints
        },
        **kwargs
    )
