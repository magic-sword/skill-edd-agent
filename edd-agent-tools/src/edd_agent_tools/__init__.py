# edd-agent-tools package
# 【名前空間デッドロック防止のための先行インポート】
try:
    from google import genai
    from google.adk.tools import ToolContext
except ImportError:
    pass

__version__ = "0.1.0"

def __getattr__(name: str):
    import importlib

    # サブモジュール自体への直接アクセスを許容し、インポートエラーを防ぎます。
    submodules = {
        "gemini",
        "skills",
        "evaluation",
        "run",
        "doc_reader",
        "models"
    }
    if name in submodules:
        return importlib.import_module(f".{name}", __package__)

    mapping = {
        # models
        "Parameter": (".models", "Parameter"),
        "SkillDesign": (".models", "SkillDesign"),
        "WorkflowDesign": (".models", "WorkflowDesign"),
        "ModuleDesign": (".models", "ModuleDesign"),
        "Step": (".models", "Step"),
        "StepType": (".models", "StepType"),
        "EvalRunResult": (".models", "EvalRunResult"),
        "SkillMetadata": (".models", "SkillMetadata"),
        "ModuleType": (".models", "ModuleType"),
        "clean_pydantic_schema": (".models", "clean_pydantic_schema"),
        # skills
        "SkillsState": (".skills", "SkillsState"),
        "Skill": (".skills", "Skill"),
        "SkillTier": (".skills", "SkillTier"),
        "WorkflowRunner": (".run.workflow", "WorkflowRunner"),
        "SafeWriteFileTool": (".run.tools", "SafeWriteFileTool"),
        "SafeEditFileTool": (".run.tools", "SafeEditFileTool"),
        # evaluation
        "SkillEval": (".evaluation", "SkillEval"),
        "UnitEval": (".evaluation", "UnitEval"),
        "TriggerEval": (".evaluation", "TriggerEval"),
        # gemini
        "GeminiClient": (".gemini", "GeminiClient"),
        "GeminiRequest": (".gemini", "GeminiRequest"),
        "gemini": (".gemini", None),
        # doc_reader
        "LibraryDocumentationReader": (".doc_reader", "LibraryDocumentationReader"),
    }

    if name in mapping:
        module_path, attr_name = mapping[name]
        module = importlib.import_module(module_path, __package__)
        if attr_name is None:
            return module
        return getattr(module, attr_name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    return sorted(list(globals().keys()) + [
        "Parameter", "SkillDesign", "WorkflowDesign", "ModuleDesign", "Step", "StepType",
        "EvalRunResult", "SkillMetadata", "ModuleType",
        "clean_pydantic_schema",
        "SkillsState", "Skill", "SkillTier", "WorkflowRunner", "SafeWriteFileTool", "SafeEditFileTool", "SkillEval", "UnitEval", "TriggerEval",
        "GeminiClient", "GeminiRequest", "gemini", "LibraryDocumentationReader"
    ])


