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

    mapping = {
        # models
        "Parameter": (".models", "Parameter"),
        "SkillDesign": (".models", "SkillDesign"),
        "EvalRunResult": (".models", "EvalRunResult"),
        "SkillMetadata": (".models", "SkillMetadata"),
        "ModuleType": (".models", "ModuleType"),
        # registry
        "SkillRegistry": (".registry", "SkillRegistry"),
        # skill
        "Skill": (".skill", "Skill"),
        # evaluation
        "SkillEval": (".evaluation", "SkillEval"),
        "UnitEval": (".evaluation", "UnitEval"),
        "TriggerEval": (".evaluation", "TriggerEval"),
        # gemini
        "GeminiClient": (".gemini", "GeminiClient"),
        "GeminiRequest": (".gemini", "GeminiRequest"),
        # doc_reader
        "LibraryDocumentationReader": (".doc_reader", "LibraryDocumentationReader"),
    }

    if name in mapping:
        module_path, attr_name = mapping[name]
        module = importlib.import_module(module_path, __package__)
        return getattr(module, attr_name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    return sorted(list(globals().keys()) + [
        "Parameter", "SkillDesign", "EvalRunResult", "SkillMetadata", "ModuleType",
        "SkillRegistry", "Skill", "SkillEval", "UnitEval", "TriggerEval",
        "GeminiClient", "GeminiRequest", "LibraryDocumentationReader"
    ])


