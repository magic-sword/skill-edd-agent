# edd-agent-tools package
# 【名前空間デッドロック防止のための先行インポート】
try:
    from google import genai
    from google.adk.tools import ToolContext
except ImportError:
    pass

__version__ = "0.2.0"

def __getattr__(name: str):
    import importlib

    submodules = {
        "gemini",
        "skills",
        "evaluation",
        "run",
        "doc_reader",
        "schema_utils",
        "mcp"
    }
    if name in submodules:
        return importlib.import_module(f".{name}", __package__)

    mapping = {
        # skills.models
        "SkillPattern": (".skills.models", "SkillPattern"),
        "SkillLogicDraft": (".skills.models", "SkillLogicDraft"),
        "SkillSpec": (".skills.models", "SkillSpec"),
        "SkillMetadata": (".skills.models", "SkillMetadata"),
        "ModuleType": (".skills.models", "ModuleType"),
        "SkillTier": (".skills.models", "SkillTier"),
        "SkillsStateJson": (".skills.models", "SkillsStateJson"),
        "SkillEntry": (".skills.models", "SkillEntry"),
        "InheritEntry": (".skills.models", "InheritEntry"),
        "ProjectSkillInfo": (".skills.models", "ProjectSkillInfo"),
        # skills components
        "SkillsState": (".skills", "SkillsState"),
        "Skill": (".skills", "Skill"),
        "SkillTests": (".skills", "SkillTests"),
        "SkillTemplateEngine": (".skills", "SkillTemplateEngine"),
        "SkillValidator": (".skills", "SkillValidator"),
        "ValidationResult": (".skills", "ValidationResult"),
        "SkillCreationEngine": (".skills", "SkillCreationEngine"),
        "create_skill": (".skills", "create_skill"),
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
        # run / tools
        "WorkflowRunner": (".run.workflow", "WorkflowRunner"),
        "merge_result_to_state": (".run.workflow", "merge_result_to_state"),
        "SafeWriteFileTool": (".run.tools", "SafeWriteFileTool"),
        "SafeEditFileTool": (".run.tools", "SafeEditFileTool"),
        # evaluation
        "SimulationEval": (".evaluation", "SimulationEval"),
        "SimulationEvalRunner": (".evaluation", "SimulationEvalRunner"),
        "LocalWorkspaceEnv": (".evaluation", "LocalWorkspaceEnv"),
        "RealWorkspaceEnv": (".evaluation", "RealWorkspaceEnv"),
        "WorkspaceEnvProtocol": (".evaluation", "WorkspaceEnvProtocol"),
        "ContractTestRunner": (".evaluation", "ContractTestRunner"),
        "TestGenerator": (".evaluation", "TestGenerator"),
        "TestExecutor": (".evaluation", "TestExecutor"),
        "TrajectoryEvalSet": (".evaluation", "TrajectoryEvalSet"),
        "CascadeTestRunner": (".evaluation", "CascadeTestRunner"),
        "EvalSetGenerator": (".evaluation", "EvalSetGenerator"),
        "generate_evalset": (".evaluation", "generate_evalset"),
        "run_evaluation": (".evaluation", "run_evaluation"),
        "run_tier_gate": (".evaluation", "run_tier_gate"),
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
        "SkillPattern", "SkillLogicDraft", "SkillSpec", "SkillMetadata", "ModuleType",
        "SkillTier", "SkillsStateJson", "SkillEntry", "InheritEntry", "ProjectSkillInfo",
        "SkillsState", "Skill", "SkillTests", "SkillTemplateEngine", "SkillValidator", "ValidationResult",
        "SkillCreationEngine", "create_skill",
        "EvalRunResult", "FailedCaseDetail", "EvalDetailReport", "WorkspaceArtifacts", "WorkspaceAction",
        "WriteFileAction", "ViewFileAction", "RunPytestAction", "WorkspaceObservation", "FileState",
        "clean_pydantic_schema", "PromptField",
        "WorkflowRunner", "merge_result_to_state", "SafeWriteFileTool", "SafeEditFileTool", 
        "SimulationEval", "SimulationEvalRunner", "LocalWorkspaceEnv", "RealWorkspaceEnv", "WorkspaceEnvProtocol", "ContractTestRunner",
        "TestGenerator", "TestExecutor", "TrajectoryEvalSet", "CascadeTestRunner",
        "EvalSetGenerator", "generate_evalset", "run_evaluation", "run_tier_gate",
        "GeminiClient", "GeminiRequest", "gemini", "LibraryDocumentationReader"
    ])

