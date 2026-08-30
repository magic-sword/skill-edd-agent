# edd-agent-tools package
# Evaluation-Driven Development (EDD) tools for AI Agents

__version__ = "0.3.0"

def __getattr__(name: str):
    import importlib

    submodules = {
        "core",
        "skills",
        "evaluation",
        "run",
        "doc_reader",
        "schema_utils",
        "mcp",
        "adk",
        "cli"
    }
    if name in submodules:
        return importlib.import_module(f".{name}", __package__)

    mapping = {
        # adk
        "EddSkillToolset": (".adk", "EddSkillToolset"),
        # core / skills models
        "SkillPattern": (".core.models", "SkillPattern"),
        "SkillLogicDraft": (".core.models", "SkillLogicDraft"),
        "SkillSpec": (".core.models", "SkillSpec"),
        "SkillMetadata": (".core.models", "SkillMetadata"),
        "ModuleType": (".core.models", "ModuleType"),
        "SkillTier": (".core.models", "SkillTier"),
        "SkillsStateJson": (".core.models", "SkillsStateJson"),
        "SkillEntry": (".core.models", "SkillEntry"),
        "InheritEntry": (".core.models", "InheritEntry"),
        "ProjectSkillInfo": (".core.models", "ProjectSkillInfo"),
        # core / skills components
        "SkillsState": (".core.state", "SkillsState"),
        "Skill": (".core.skill", "Skill"),
        "SkillTests": (".skills.tests", "SkillTests"),
        "SkillTemplateEngine": (".skills.template_engine", "SkillTemplateEngine"),
        "SkillValidator": (".skills.validator", "SkillValidator"),
        "ValidationResult": (".skills.validator", "ValidationResult"),
        "SkillCreationEngine": (".skills.creator", "SkillCreationEngine"),
        "create_skill": (".skills.creator", "create_skill"),
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
        "WorkspaceEnvProtocol": (".core.protocols", "WorkspaceEnvProtocol"),
        "ContractTestRunner": (".evaluation", "ContractTestRunner"),
        "TestGenerator": (".evaluation", "TestGenerator"),
        "TestExecutor": (".evaluation", "TestExecutor"),
        "TrajectoryEvalSet": (".evaluation", "TrajectoryEvalSet"),
        "CascadeTestRunner": (".evaluation", "CascadeTestRunner"),
        "SkillDiagnoser": (".evaluation", "SkillDiagnoser"),
        "EvalSetGenerator": (".evaluation", "EvalSetGenerator"),
        "generate_evalset": (".evaluation", "generate_evalset"),
        "run_evaluation": (".evaluation", "run_evaluation"),
        "run_tier_gate": (".evaluation", "run_tier_gate"),
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
        "EddSkillToolset",
        "SkillPattern", "SkillLogicDraft", "SkillSpec", "SkillMetadata", "ModuleType",
        "SkillTier", "SkillsStateJson", "SkillEntry", "InheritEntry", "ProjectSkillInfo",
        "SkillsState", "Skill", "SkillTests", "SkillTemplateEngine", "SkillValidator", "ValidationResult",
        "SkillCreationEngine", "create_skill",
        "EvalRunResult", "FailedCaseDetail", "EvalDetailReport", "WorkspaceArtifacts", "WorkspaceAction",
        "WriteFileAction", "ViewFileAction", "RunPytestAction", "WorkspaceObservation", "FileState",
        "clean_pydantic_schema", "PromptField",
        "WorkflowRunner", "merge_result_to_state", "SafeWriteFileTool", "SafeEditFileTool", 
        "SimulationEval", "SimulationEvalRunner", "LocalWorkspaceEnv", "RealWorkspaceEnv", "WorkspaceEnvProtocol", "ContractTestRunner",
        "TestGenerator", "TestExecutor", "TrajectoryEvalSet", "CascadeTestRunner", "SkillDiagnoser",
        "EvalSetGenerator", "generate_evalset", "run_evaluation", "run_tier_gate",
        "LibraryDocumentationReader"
    ])
