def remove_additional_properties(schema: dict) -> dict:
    """JSONスキーマから Gemini Developer API で未サポートの 'additionalProperties' を再帰的に削除します。"""
    if not isinstance(schema, dict):
        return schema
    schema.pop("additionalProperties", None)
    for key, value in schema.items():
        if isinstance(value, dict):
            remove_additional_properties(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    remove_additional_properties(item)
    return schema
