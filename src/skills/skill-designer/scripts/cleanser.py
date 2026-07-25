class DesignCleanser:
    """LLMが出力した設計データ（dict）に対する最小限の決定論的クレンジング処理。"""
    def clean(self, design_data: dict) -> dict:
        if not isinstance(design_data, dict):
            return design_data

        # 1. スキル名を小文字ハイフン区切りに整形
        if "name" in design_data and isinstance(design_data["name"], str):
            design_data["name"] = self._clean_name(design_data["name"])

        # 2. module_type が skill の場合、不要な steps を除去
        m_type = design_data.get("module_type", "skill")
        if m_type != "workflow":
            design_data.pop("steps", None)

        return design_data

    def _clean_name(self, name: str) -> str:
        return name.lower().replace("_", "-").replace(" ", "-")
