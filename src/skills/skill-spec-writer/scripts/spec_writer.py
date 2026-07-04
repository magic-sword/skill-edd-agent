import os
import sys
import json
from google.adk.tools import ToolContext
from .writer.factory import SpecWriterFactory

def process_message(tool_context: ToolContext):
    """
    spec-writer のメインビジネスロジック。
    仕様書 (SKILL.md) を自動生成します。
    """
    design_path = tool_context.state.get("design_path")
    name = tool_context.state.get("name")
    output_dir = tool_context.state.get("output_dir")
    source_code_dir = tool_context.state.get("source_code_dir")

    from edd_agent_tools.models import SkillDesign
    from edd_agent_tools.registry import SkillRegistry

    # スキルレジストリのロード
    registry = SkillRegistry()
    registry.load()

    # 1. 共通パス特定
    resolved = None
    target_name = name
    if not target_name and design_path:
        if not os.path.isabs(design_path):
            tmp_path = os.path.abspath(os.path.join("/workspace", design_path))
        else:
            tmp_path = design_path
        if os.path.exists(tmp_path) and not os.path.isdir(tmp_path):
            try:
                with open(tmp_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    if isinstance(old_data, dict) and old_data.get("name"):
                        target_name = old_data["name"]
            except Exception:
                pass

    if target_name:
        resolved = registry.resolve_skill_paths(target_name)
        if not design_path:
            design_path = resolved["design_path"]
        if not output_dir:
            output_dir = resolved["component_root"]
        if not source_code_dir:
            source_code_dir = resolved["source_code_dir"]

    # パスの補正とロード
    if not design_path:
        raise ValueError("Error: Either 'name' or 'design_path' must be provided.")

    if not os.path.isabs(design_path):
        design_path = os.path.abspath(os.path.join("/workspace", design_path))

    if not os.path.exists(design_path) or os.path.isdir(design_path):
        raise FileNotFoundError(f"Error: design.json file not found at '{design_path}'.")

    # design.json ファイルから直接 SkillDesign をロード
    try:
        with open(design_path, "r", encoding="utf-8") as f:
            design_data = SkillDesign.model_validate_json(f.read())
    except Exception as e:
        raise ValueError(f"Error loading and validating design.json: {e}")

    # component_root の再特定
    component_root = registry.get_skill_dir(design_data.name)
    if not component_root:
        dir_name = os.path.dirname(design_path)
        if os.path.basename(dir_name) == "assets":
            component_root = os.path.dirname(dir_name)
        else:
            component_root = dir_name

    # 2. output_dir の解決
    if not output_dir:
        output_dir = component_root

    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(os.path.join("/workspace", output_dir))


    # 3. 実装コードのロード (ディレクトリ内の全Pythonファイルの結合スキャン、または単一ファイル)
    source_code = ""
    scan_target = None

    if source_code_dir:
        if not os.path.isabs(source_code_dir):
            source_code_dir = os.path.abspath(os.path.join("/workspace", source_code_dir))
        scan_target = source_code_dir
    elif component_root:
        scan_target = os.path.join(component_root, "scripts")

    if scan_target and os.path.exists(scan_target):
        if os.path.isdir(scan_target):
            py_files = []
            for root, dirs, files in os.walk(scan_target):
                for f in files:
                    if f.endswith(".py"):
                        py_files.append(os.path.join(root, f))
            
            if py_files:
                print(f"Detected {len(py_files)} source files for scanning under {scan_target}.")
                combined_code = []
                # 相対パス記述用の基準ルート
                ref_root = component_root if component_root else os.path.dirname(scan_target)
                for file_path in sorted(py_files):
                    rel_path = os.path.relpath(file_path, ref_root)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        combined_code.append(f"# --- File: {rel_path} ---\n{content}")
                    except Exception as e:
                        print(f"Warning: Failed to read {file_path}: {e}")
                source_code = "\n\n".join(combined_code)
        else:
            # 単一ファイル直接ロードの場合
            print(f"Loading specified single source file: {scan_target}")
            try:
                with open(scan_target, "r", encoding="utf-8") as f:
                    source_code = f.read()
            except Exception as e:
                print(f"Warning: Failed to read {scan_target}: {e}")

    print(f"Starting specification generation for skill: {design_data.name}")
    print(f"Design Path: {design_path}")
    print(f"Output Directory: {output_dir}")

    # execution_type に基づいて適切な具象ライターを構築して実行
    try:
        writer = SpecWriterFactory.create(
            execution_type=design_data.execution_type,
            design_data=design_data,
            source_code=source_code,
            source_code_dir=source_code_dir,
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
