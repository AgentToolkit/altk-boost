from typing import Union, List

from altk.pre_tool.toolguard.toolguard.data_types import ToolPolicy
from altk.pre_tool.toolguard.toolguard.runtime import ToolGuardsCodeGenerationResult
from altk.core.toolkit import ComponentInput, ComponentOutput
from altk.core.llm import BaseLLMClient
from pydantic import BaseModel, Field, ConfigDict


class ToolGuardBuildInputMetaData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    policy_text: str = Field(description="Text of the policy document file")
    short1: bool = Field(default=True, description="Run build short or long version. ")
    validating_llm_client: BaseLLMClient = Field(
        description="ValidatingLLMClient for build time"
    )


class ToolGuardBuildInput(ComponentInput):
    metadata: ToolGuardBuildInputMetaData = Field(
        default_factory=lambda: ToolGuardBuildInputMetaData()
    )


class ToolGuardRunInputMetaData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    tool_name: str = Field(description="Tool name")
    tool_parms: dict = Field(default={}, description="Tool parameters")
    # llm_client: LLMClient = Field(description="LLMClient for build time")


class ToolGuardRunInput(ComponentInput):
    metadata: ToolGuardRunInputMetaData = Field(
        default_factory=lambda: ToolGuardRunInputMetaData()
    )


class ToolGuardBuildOutputMetaData(BaseModel):
    tool_policies: List[ToolPolicy] = (
        Field(
            description="List of policies specs for each tool extracted from the policy document"
        ),
    )
    generated_code_object: ToolGuardsCodeGenerationResult = Field(
        description="root_dir of the generated code object, runtime domain and code for each tool guard"
    )


class ToolGuardBuildOutput(ComponentOutput):
    output: ToolGuardBuildOutputMetaData = Field(
        default_factory=lambda: ToolGuardBuildOutputMetaData()
    )


class ToolGuardRunOutputMetaData(BaseModel):
    error_message: Union[str, bool] = Field(
        description="Error string or False if no error occurred"
    )


class ToolGuardRunOutput(ComponentOutput):
    output: ToolGuardRunOutputMetaData = Field(
        default_factory=lambda: ToolGuardRunOutputMetaData()
    )
