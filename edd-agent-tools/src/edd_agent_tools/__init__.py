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
        "schema_utils"
    }
    if name in submodules:
        return importlib.import_module(f".{name}", __package__)

    mapping = {
        # skills.models
        "Parameter": (".skills.models", "Parameter"),
        "SkillDesign": (".skills.models", "SkillDesign"),
        "WorkflowDesign": (".skills.models", "WorkflowDesign"),
        "ModuleDesign": (".skills.models", "ModuleDesign"),
        "Step": (".skills.models", "Step"),
        "StepType": (".skills.models", "StepType"),
        "SkillMetadata": (".skills.models", "SkillMetadata"),
        "ModuleType": (".skills.models", "ModuleType"),
        # evaluation.models
        "EvalRunResult": (".evaluation.models", "EvalRunResult"),
        "FailedCaseDetail": (".evaluation.models", "FailedCaseDetail"),
        "EvalDetailReport": (".evaluation.models", "EvalDetailReport"),
        "WorkspaceArtifacts": (".evaluation.models", "WorkspaceArtifacts"),
        "WorkspaceAction": (".evaluation.models", "WorkspaceAction"),
        "WriteFileAction": (".evaluation.models", "WriteFileAction"),
        "ViewFileAction": (".evaluation.models", "ViewFileAction"),
        "RunPytestAction": (".evaluation.models", "RunPytestAction"),
        "WorkspaceObservation": (".evaluation.models", "WorkspaceObservation"),
        "FileState": (".evaluation.models", "FileState"),
        # schema_utils
        "clean_pydantic_schema": (".schema_utils", "clean_pydantic_schema"),
        "PromptField": (".schema_utils", "PromptField"),
        # skills
        "SkillsState": (".skills", "SkillsState"),
        "Skill": (".skills", "Skill"),
        "SkillTests": (".skills", "SkillTests"),
        "SkillTier": (".skills", "SkillTier"),
        "WorkflowRunner": (".run.workflow", "WorkflowRunner"),
        "merge_result_to_state": (".run.workflow", "merge_result_to_state"),
        "SafeWriteFileTool": (".run.tools", "SafeWriteFileTool"),
        "SafeEditFileTool": (".run.tools", "SafeEditFileTool"),
        # evaluation
        "SimulationEval": (".evaluation", "SimulationEval"),
        "LocalWorkspaceEnv": (".evaluation", "LocalWorkspaceEnv"),
        "RealWorkspaceEnv": (".evaluation", "RealWorkspaceEnv"),
        "WorkspaceEnvProtocol": (".evaluation", "WorkspaceEnvProtocol"),
        "ContractTestRunner": (".evaluation", "ContractTestRunner"),
        "TestGenerator": (".evaluation", "TestGenerator"),
        "TestExecutor": (".evaluation", "TestExecutor"),
        "TrajectoryEvalSet": (".evaluation", "TrajectoryEvalSet"),
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
        "SkillMetadata", "ModuleType", "EvalRunResult", "FailedCaseDetail", "EvalDetailReport", "WorkspaceArtifacts", "WorkspaceAction",
        "WriteFileAction", "ViewFileAction", "RunPytestAction", "WorkspaceObservation", "FileState",
        "clean_pydantic_schema", "PromptField",
        "SkillsState", "Skill", "SkillTests", "SkillTier", "WorkflowRunner", "merge_result_to_state", "SafeWriteFileTool", "SafeEditFileTool", 
        "SimulationEval", "LocalWorkspaceEnv", "RealWorkspaceEnv", "WorkspaceEnvProtocol", "ContractTestRunner",
        "TestGenerator", "TestExecutor", "TrajectoryEvalSet",
        "GeminiClient", "GeminiRequest", "gemini", "LibraryDocumentationReader"
    ])

