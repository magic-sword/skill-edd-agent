from pydantic import BaseModel

class PydanticModelParser:
    """
    Pydantic (V2) モデルを解析し、アタッチされているバリデータから
    ドキュメント用制約条件を決定論的に抽出するパーサーユーティリティ。
    """
    @staticmethod
    def parse_constraints(model_cls: type[BaseModel]) -> list[str]:
        constraints = []
        # model_cls から Pydantic デコレータ情報を取得
        decorators = getattr(model_cls, "__pydantic_decorators__", None)
        if not decorators:
            return constraints

        # model_validators の Docstring を抽出
        if hasattr(decorators, "model_validators"):
            for val_info in decorators.model_validators.values():
                func = getattr(val_info, "func", None)
                if func and func.__doc__:
                    doc = func.__doc__.strip()
                    if doc:
                        constraints.append(doc)

        # field_validators の Docstring を抽出
        if hasattr(decorators, "field_validators"):
            for val_info in decorators.field_validators.values():
                func = getattr(val_info, "func", None)
                if func and func.__doc__:
                    doc = func.__doc__.strip()
                    if doc:
                        fields_str = ", ".join(val_info.fields)
                        constraints.append(f"{fields_str}: {doc}")

        return constraints
