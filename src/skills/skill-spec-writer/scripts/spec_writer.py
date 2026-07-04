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

    import importlib
    from edd_agent_tools.models import Parameter, SkillDesign
    from edd_agent_tools.registry import SkillRegistry

    # スキル/ワークフローのルートディレクトリを特定
    registry = SkillRegistry()
    registry.load()
    component_root = registry.get_skill_dir(name)
    
    if not component_root:
        if design_path and os.path.exists(design_path):
            if os.path.isdir(design_path):
                component_root = design_path
            else:
                component_root = os.path.dirname(os.path.dirname(design_path))
        else:
            raise ValueError(f"Error: Could not locate directory for skill: {name}")
            
    try:
        handler_module = registry.load_handler(name)
        print(f"DEBUG spec_writer: Loaded module {handler_module.__name__} from {getattr(handler_module, '__file__', 'unknown')}")
        print(f"DEBUG spec_writer: SKILL_METADATA = {getattr(handler_module, 'SKILL_METADATA', {})}")
    except Exception as e:
        raise ValueError(f"Error loading handler.py for '{name}': {e}")
        
    metadata = getattr(handler_module, "SKILL_METADATA", {})
    InputSchema = getattr(handler_module, "Input", None)
    
    # Input から Parameter のリストを生成
    params = []
    if InputSchema:
        for f_name, f_info in InputSchema.model_fields.items():
            f_type = f_info.annotation
            
            from typing import get_args, get_origin, Union
            origin = get_origin(f_type)
            if origin is Union:
                args_types = [a for a in get_args(f_type) if a is not type(None)]
                if args_types:
                    f_type = args_types[0]
                    
            type_str = getattr(f_type, "__name__", str(f_type))
            required = f_info.is_required()
            default_val = str(f_info.default) if (not required and f_info.default is not None) else None
            
            params.append(Parameter(
                name=f_name,
                type=type_str,
                description=f_info.description or "",
                required=required,
                default=default_val
            ))
            
    design_data = SkillDesign(
        name=metadata.get("name", name),
        description=metadata.get("description", ""),
        execution_type=metadata.get("execution_type", "tool"),
        output_mode=metadata.get("output_mode", "VALUE_ONLY"),
        parameters=params,
        dependencies=metadata.get("dependencies", [])
    )

    # 実装コードのロード (オプション、未指定時は自動検知)
    source_code = ""
    
    if not source_code_path and component_root:
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
