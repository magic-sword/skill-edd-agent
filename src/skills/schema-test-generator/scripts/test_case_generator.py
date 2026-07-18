import uuid
from typing import List, Any
from edd_agent_tools.evaluation import EvalCase, EvalCaseSet
from .types import DesignJson, Function, Parameter

class TestCaseGenerator:
    """DesignJsonオブジェクトから単体テストケース（正常系、異常系）を生成するクラス。"""

    def generate_test_cases(self, design_json: DesignJson) -> EvalCaseSet:
        """
        DesignJsonオブジェクトに基づいてテストケースを生成します。

        Args:
            design_json: テストケースを生成する対象のDesignJsonオブジェクト。

        Returns:
            生成されたEvalCaseSetオブジェクト。
        """
        all_cases: List[EvalCase] = []

        for func in design_json.functions:
            self._generate_normal_cases(func, all_cases)
            self._generate_abnormal_cases(func, all_cases)

        return EvalCaseSet(
            eval_set_id=f"{design_json.name}_unit_test_set",
            eval_cases=all_cases
        )

    def _generate_normal_cases(self, func: Function, all_cases: List[EvalCase]):
        """正常系テストケースを生成します。"""
        case_id = f"{func.name}_normal_01_{str(uuid.uuid4())[:8]}"
        input_params = {}
        for param in func.parameters:
            if param.example is not None:
                input_params[param.name] = param.example
            elif param.required and param.default is None:
                input_params[param.name] = self._generate_dummy_value_for_type(param.type)
            elif param.default is not None:
                input_params[param.name] = param.default

        all_cases.append(
            EvalCase(
                eval_case_id=case_id,
                function_name=func.name,
                inputs=input_params,
                expected="success"
            )
        )

    def _generate_abnormal_cases(self, func: Function, all_cases: List[EvalCase]):
        """異常系テストケースを生成します。"""
        for param in func.parameters:
            abnormal_input = self._generate_abnormal_value(param)
            if abnormal_input is not None:
                case_id = f"{func.name}_{param.name}_abnormal_{str(uuid.uuid4())[:8]}"
                input_params = {}
                for other_param in func.parameters:
                    if other_param.name == param.name:
                        input_params[other_param.name] = abnormal_input
                    elif other_param.example is not None:
                        input_params[other_param.name] = other_param.example
                    elif other_param.required and other_param.default is None:
                        input_params[other_param.name] = self._generate_dummy_value_for_type(other_param.type)
                    elif other_param.default is not None:
                        input_params[other_param.name] = other_param.default

                all_cases.append(
                    EvalCase(
                        eval_case_id=case_id,
                        function_name=func.name,
                        inputs=input_params,
                        expected="ValidationError"
                    )
                )
            
            # requiredパラメータで、exampleもdefaultもない場合に、パラメータを渡さないケースも異常系として追加
            if param.required and param.example is None and param.default is None:
                case_id = f"{func.name}_{param.name}_abnormal_missing_required_{str(uuid.uuid4())[:8]}"
                input_params = {}
                for other_param in func.parameters:
                    if other_param.name != param.name:
                        if other_param.example is not None:
                            input_params[other_param.name] = other_param.example
                        elif other_param.required and other_param.default is None:
                            input_params[other_param.name] = self._generate_dummy_value_for_type(other_param.type)
                        elif other_param.default is not None:
                            input_params[other_param.name] = other_param.default
                
                all_cases.append(
                    EvalCase(
                        eval_case_id=case_id,
                        function_name=func.name,
                        inputs=input_params,
                        expected="ValidationError"
                    )
                )

    def _generate_abnormal_value(self, param: Parameter) -> Any:
        """パラメータの制約に基づいて異常値を生成します。"""
        # choices
        if param.choices:
            if param.type == "str":
                return "not_in_choices_string"
            elif param.type == "int":
                return 99999999
            elif param.type == "bool":
                return "invalid_bool"

        # ge (greater than or equal)
        if param.ge is not None:
            if param.type == "int" or param.type == "float":
                return param.ge - 1

        # le (less than or equal)
        if param.le is not None:
            if param.type == "int" or param.type == "float":
                return param.le + 1

        # min_length
        if param.min_length is not None and param.type == "str":
            return "a" * (param.min_length - 1) if param.min_length > 0 else ""

        # max_length
        if param.max_length is not None and param.type == "str":
            return "a" * (param.max_length + 1)

        # pattern
        if param.pattern is not None and param.type == "str":
            return "invalid-pattern-string-123!"

        return None

    def _generate_dummy_value_for_type(self, param_type: str) -> Any:
        """型に基づいてダミー値を生成します。"""
        if param_type == "str":
            return "dummy_string"
        elif param_type == "int":
            return 0
        elif param_type == "bool":
            return False
        elif param_type == "float":
            return 0.0
        elif param_type == "list":
            return []
        elif param_type == "dict":
            return {}
        else:
            return None
