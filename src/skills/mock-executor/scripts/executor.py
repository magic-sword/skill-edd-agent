import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools import EvalRunResult, SkillRegistry

from .models import Input, Output

class SkillExecutor:
    """Executes ADK evaluation simulations and validates the results.

    This class encapsulates the business logic for running ADK evaluation simulations
    against a specified skill and determining if the evaluation passes based on
    a given accuracy threshold.

    Attributes:
        params: Input parameters for the skill execution.
        tool_context: The tool context providing access to state and other utilities.
        _registry: An instance of SkillRegistry for accessing skill definitions.
    """
    def __init__(self, params: Input, tool_context: ToolContext):
        """Initializes the SkillExecutor with input parameters and tool context.

        Args:
            params: The input parameters provided to the skill.
            tool_context: The tool context for managing skill state and interactions.
        """
        self.params = params
        self.tool_context = tool_context
        self._registry = SkillRegistry()

    def execute(self) -> Output:
        """Executes the ADK evaluation simulation and validates the results.

        This method orchestrates the evaluation process, including retrieving the
        target skill, running the evaluation set, and processing the results
        against the defined accuracy threshold.

        Returns:
            An Output object containing the evaluation result message.

        Raises:
            ValueError: If the skill name is not provided.
            FileNotFoundError: If the specified evaluation set or configuration file is not found.
            RuntimeError: If an unexpected error occurs during evaluation or if the evaluation fails.
        """
        try:
            skill_name = self.params.skill
            if not skill_name:
                raise ValueError("'skill' parameter is required.")

            target_skill = self._registry.get_skill(name=skill_name)
            
            eval_set_path = self.params.eval_set_path
            eval_obj = target_skill.get_eval(eval_set_path)

            print(f"Running mock-executor for skill: {skill_name}")
            print(f"Eval set: {eval_set_path}")
            
            threshold_accuracy = self.params.threshold_accuracy
            timeout_seconds = self.params.timeout_seconds
            print(f"Threshold accuracy: {threshold_accuracy:.4f}, Timeout: {timeout_seconds}s")

            eval_result = eval_obj.execute(
                timeout_seconds=timeout_seconds,
                config_file_path=self.params.config_file_path
            )
            
            output_message = self._process_eval_result(eval_result, threshold_accuracy)

            return Output(value=output_message)

        except FileNotFoundError as e:
            error_message = f"File not found: {e}"
            self._update_state_on_error(error_message, 0.0, self.params.threshold_accuracy or 1.0)
            print(f"Error: {error_message}", file=sys.stderr)
            raise RuntimeError(error_message) from e
        except ValueError as e:
            error_message = str(e)
            self._update_state_on_error(error_message, 0.0, self.params.threshold_accuracy or 1.0)
            print(f"Error: {error_message}", file=sys.stderr)
            raise RuntimeError(error_message) from e
        except RuntimeError as e:
            error_message = str(e)
            # If _process_eval_result already updated the state, skip updating again.
            if "status" not in self.tool_context.state:
                self._update_state_on_error(error_message, 0.0, self.params.threshold_accuracy or 1.0)
            print(f"Error: {error_message}", file=sys.stderr)
            raise
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            self._update_state_on_error(error_message, 0.0, self.params.threshold_accuracy or 1.0)
            print(f"Unexpected error: {error_message}", file=sys.stderr)
            raise RuntimeError(error_message) from e

    def _process_eval_result(self, result: EvalRunResult, threshold_accuracy: float) -> str:
        """Processes the evaluation result, determines pass/fail, generates a message, and updates `ToolContext.state`.

        Args:
            result: The `EvalRunResult` object containing the raw evaluation outcomes.
            threshold_accuracy: The minimum accuracy required for the evaluation to pass.

        Returns:
            A string message summarizing the evaluation outcome.

        Raises:
            RuntimeError: If the evaluation result indicates a failure.
        """
        accuracy = result.accuracy
        print(f"Evaluation result: Passed = {result.passed}, Failed = {result.failed}, Total = {result.total}, Accuracy = {accuracy:.4f}")

        status = "passed" if accuracy >= threshold_accuracy else "failed"
        message = f"Accuracy {accuracy:.4f} is {'greater than or equal to' if status == 'passed' else 'less than'} threshold {threshold_accuracy:.4f}."
        if status == "failed" and result.detail_file_path:
            message += f"\nFor detailed failure reasons, please refer to the result file:\n{result.detail_file_path}"
        
        self.tool_context.state.update({
            "status": status,
            "message": message,
            "accuracy": accuracy,
            "threshold_accuracy": threshold_accuracy
        })

        if status == "passed":
            print(f"\n🎉 Test passed! Accuracy {accuracy:.4f} >= Threshold {threshold_accuracy:.4f}")
            return message
        else:
            print(f"\n❌ Test failed! Accuracy {accuracy:.4f} < Threshold {threshold_accuracy:.4f}", file=sys.stderr)
            raise RuntimeError(message)

    def _update_state_on_error(self, error_message: str, accuracy: float, threshold: float):
        """Updates the `tool_context.state` when an error occurs during evaluation.

        Args:
            error_message: The error message to be stored in the state.
            accuracy: The accuracy value to record (typically 0.0 on error).
            threshold: The threshold accuracy against which the evaluation was run.
        """
        self.tool_context.state.update({
            "status": "failed",
            "message": error_message,
            "accuracy": accuracy,
            "threshold_accuracy": threshold
        })
