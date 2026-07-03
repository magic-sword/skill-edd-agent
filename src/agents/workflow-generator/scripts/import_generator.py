import os
import json

def insert_tool_imports(output_dir: str) -> int:
    """
    design.json から dependencies を読み込み、
    workflow.py のプレースホルダーへ決定論的にインポート文 (load_tool) を挿入します。
    """
    design_json_path = os.path.join(output_dir, "assets", "design.json")
    if not os.path.exists(design_json_path):
        print(f"[Import Generator Warning]: {design_json_path} が見つからないため、インポートの挿入をスキップします。")
        return 0

    try:
        with open(design_json_path, "r", encoding="utf-8") as f:
            design_data = json.load(f)
        
        dependencies = design_data.get("dependencies", [])
        
        # インポートコードの組み立て
        import_lines = ["# 依存するスキルからツールを動的ロード"]
        for dep in dependencies:
            dep_skill_name = dep.get("skill")
            dep_functions = dep.get("functions", [])
            if dep_skill_name and dep_functions:
                for func_name in dep_functions:
                    import_lines.append(f'{func_name} = registry.load_tool("{dep_skill_name}", "{func_name}")')
        
        import_code = "\n".join(import_lines)
        
        # workflow.py のインポートプレースホルダー置換
        workflow_py_path = os.path.join(output_dir, "scripts", "workflow.py")
        if os.path.exists(workflow_py_path):
            with open(workflow_py_path, "r", encoding="utf-8") as f:
                wf_content = f.read()
            
            target_placeholder = '# [TODO] 依存するスキルからツールをロード\n# 例: set_skill_tier = registry.load_tool("skill-manager", "set_skill_tier")'
            if target_placeholder in wf_content:
                wf_content = wf_content.replace(target_placeholder, import_code)
            else:
                wf_content = wf_content.replace("# [TODO] 依存するスキルからツールをロード", import_code)
                
            with open(workflow_py_path, "w", encoding="utf-8") as f:
                f.write(wf_content)
            print(f"[Import Generator]: scripts/workflow.py に {len(import_lines) - 1} 個のツールロード定義を自動挿入しました。")
            return len(import_lines) - 1
            
    except Exception as e:
        print(f"[Import Generator Error]: インポート自動挿入中にエラーが発生しました: {e}")
        
    return 0
