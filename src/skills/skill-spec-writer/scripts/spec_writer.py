import os
import sys
import json
from google.adk.tools import ToolContext
from .writer.factory import SpecWriterFactory

def process_message(tool_context: ToolContext):
    """
    spec-writer のメインビジネスロジック。
    入力パラメータに基づいて適切なライター（Skill / Workflow）を選択し、
    仕様書 (SKILL.md) を自動生成します。
    """
    target_type = tool_context.state.get("target_type") # "skill" or "workflow"
    name = tool_context.state.get("name")
    design_path = tool_context.state.get("design_path")
    source_code_path = tool_context.state.get("source_code_path")
    output_dir = tool_context.state.get("output_dir")

    if not target_type or not name or not design_path or not output_dir:
        raise ValueError("Error: 'target_type', 'name', 'design_path', and 'output_dir' are all required parameters.")

    # パスの補正
    if not os.path.isabs(design_path):
        design_path = os.path.abspath(os.path.join("/workspace", design_path))
        
    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(os.path.join("/workspace", output_dir))

    from edd_agent_tools.models import SkillDesign

    # 設計データのロード & バリデーション
    if not os.path.exists(design_path):
        raise FileNotFoundError(f"Error: Design JSON not found at {design_path}")
    with open(design_path, "r", encoding="utf-8") as f:
        design_json_data = json.load(f)
        
    try:
        design_data = SkillDesign.model_validate(design_json_data)
    except Exception as e:
        raise ValueError(f"Error validating design.json: {e}")

    # 実装コードのロード (オプション、未指定時は自動検知)
    source_code = ""
    
    if not source_code_path and design_path:
        # design_path (例: src/skills/<name>/assets/design.json) からコンポーネントルートを導出
        component_root = os.path.dirname(os.path.dirname(design_path))
        scripts_dir = os.path.join(component_root, "scripts")
        
        if os.path.exists(scripts_dir):
            py_files = [f for f in os.listdir(scripts_dir) if f.endswith(".py") and f != "__init__.py"]
            
            if "main.py" in py_files:
                source_code_path = os.path.join(scripts_dir, "main.py")
            else:
                expected_name = f"{name.replace('-', '_')}.py"
                if expected_name in py_files:
                    source_code_path = os.path.join(scripts_dir, expected_name)
                elif len(py_files) == 1:
                    source_code_path = os.path.join(scripts_dir, py_files[0])
                elif len(py_files) > 1:
                    # 特定できない場合は最初の候補を選択
                    source_code_path = os.path.join(scripts_dir, py_files[0])

    if source_code_path:
        if not os.path.isabs(source_code_path):
            source_code_path = os.path.abspath(os.path.join("/workspace", source_code_path))
        if os.path.exists(source_code_path):
            print(f"Automatically detected source code path: {source_code_path}")
            with open(source_code_path, "r", encoding="utf-8") as f:
                source_code = f.read()

    print(f"Starting specification generation for {target_type}: {name}")
    print(f"Design Path: {design_path}")
    print(f"Output Directory: {output_dir}")

    # ファクトリパターンによる具象ライターの構築と実行
    try:
        writer = SpecWriterFactory.create(
            target_type=target_type,
            name=name,
            design_data=design_data,
            source_code=source_code,
            source_code_path=source_code_path,
            tool_context=tool_context
        )
        
        output_file_path = writer.generate(output_dir)
        
        print(f"🎉 Successfully generated specification at: {output_file_path}")
        
        tool_context.state.update({
            "status": "success",
            "message": f"Successfully generated specification at: {output_file_path}",
            "output_file_path": output_file_path
        })
    except Exception as e:
        print(f"❌ Error during specification generation: {e}", file=sys.stderr)
        tool_context.state.update({
            "status": "failed",
            "message": str(e)
        })
        raise e
