from pydantic import BaseModel, Field
from typing import List, Optional, Any, Literal

# design.json のスキーマを表現するPydanticモデル
class Parameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool
    default: Optional[Any] = None
    choices: Optional[List[Any]] = None
    ge: Optional[float] = None  # Greater than or equal to
    le: Optional[float] = None  # Less than or equal to
    items_type: Optional[str] = None
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    is_prompt_parameter: Optional[bool] = None
    prompt_instructions: Optional[str] = None
    prompt_constraints: Optional[str] = None
    example: Optional[Any] = None

class ResponseParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool
    default: Optional[Any] = None
    choices: Optional[List[Any]] = None
    ge: Optional[float] = None
    le: Optional[float] = None
    items_type: Optional[str] = None
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    is_prompt_parameter: Optional[bool] = None
    prompt_instructions: Optional[str] = None
    prompt_constraints: Optional[str] = None
    example: Optional[Any] = None
    response_type: Optional[Any] = None # これは function の response_type と混同しないように注意

class Function(BaseModel):
    name: str
    description: str
    parameters: List[Parameter]
    response_parameters: Optional[List[ResponseParameter]] = None
    response_type: Optional[str] = None

class DesignJson(BaseModel):
    rationale: Optional[str] = None
    name: str
    description: str
    summary: Optional[str] = None
    module_type: str
    execution_type: str
    output_mode: str
    dependencies: List[Any]
    constraints: List[Any]
    functions: List[Function]


