import json
import os
import pytest
from unittest.mock import patch

from altk.pre_tool.core import (
    SPARCReflectionRunInput,
    SPARCReflectionDecision,
    SPARCExecutionMode,
    Track,
)
from altk.pre_tool.sparc import (
    SPARCReflectionComponent,
)
from altk.core.toolkit import AgentPhase, ComponentConfig
from altk.core.llm import get_llm
from altk.pre_tool.sparc.function_calling.pipeline.types import (
    PipelineResult,
    FunctionCallInput,
    SemanticResult,
    SemanticCategoryResult,
    SemanticMetricResult,
    TransformResult,
)
from dotenv import load_dotenv

load_dotenv()


class TestErrorHandling:
    """Test suite for error handling functionality in SPARC."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing."""
        # Build ComponentConfig with WatsonX ValidatingLLMClient
        WATSONX_CLIENT = get_llm("watsonx.output_val")
        config = ComponentConfig(
            llm_client=WATSONX_CLIENT(
                model_id="meta-llama/llama-3-3-70b-instruct",
                api_key=os.getenv("WX_API_KEY"),
                project_id=os.getenv("WX_PROJECT_ID"),
                url=os.getenv("WX_URL", "https://us-south.ml.cloud.ibm.com"),
            )
        )
        return SPARCReflectionComponent(
            config=config,
            track=Track.FAST_TRACK,
            execution_mode=SPARCExecutionMode.SYNC,
        )

    @pytest.fixture
    def tool_specs(self):
        """Basic tool specifications for testing."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City name",
                            },
                            "units": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "Temperature units",
                            },
                        },
                        "required": ["location"],
                    },
                },
            }
        ]

    @pytest.fixture
    def basic_messages(self):
        """Basic conversation messages for testing."""
        return [
            {"role": "user", "content": "What's the weather in New York?"},
            {"role": "assistant", "content": "I'll check the weather for you."},
        ]

    @pytest.fixture
    def basic_tool_call(self):
        """Basic tool call for testing."""
        return {
            "id": "1",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({"location": "New York"}),
            },
        }

    def test_function_selection_metric_error(
        self, middleware, tool_specs, basic_messages, basic_tool_call
    ):
        """Test error in function selection metric."""
        # Create a mock pipeline result with error in function selection metric
        mock_metric = SemanticMetricResult(
            metric_name="function_selection_appropriateness",
            jsonschema={},
            prompt="test prompt",
            raw_response={},
            numeric_thresholds_checks={},
            is_important=True,
            importance_reason=None,
            error="LLM timeout: Request timed out after 30 seconds",
            is_correct=False,
            is_issue=False,
        )

        mock_pipeline_result = PipelineResult(
            inputs=FunctionCallInput(
                conversation_context=basic_messages,
                tools_inventory=tool_specs,
                tool_call=basic_tool_call,
            ),
            static=None,
            semantic=SemanticResult(
                function_selection=SemanticCategoryResult(
                    metrics={"function_selection_appropriateness": mock_metric},
                    final_decision=False,
                ),
                general=None,
                parameter=None,
                transform=None,
            ),
            overall_valid=False,
        )

        # Build input
        run_input = SPARCReflectionRunInput(
            messages=basic_messages,
            tool_specs=tool_specs,
            tool_calls=[basic_tool_call],
        )

        # Patch the pipeline to return our mock result
        with patch.object(
            middleware._pipeline, "run_sync", return_value=mock_pipeline_result
        ):
            result = middleware.process(run_input, phase=AgentPhase.RUNTIME)

        # Assert that decision is ERROR
        assert result.output.reflection_result.decision == SPARCReflectionDecision.ERROR

        # Assert that error information is captured in issues
        assert len(result.output.reflection_result.issues) > 0
        error_issues = [
            issue
            for issue in result.output.reflection_result.issues
            if "LLM timeout" in issue.explanation
            or "error" in issue.explanation.lower()
        ]
        assert len(error_issues) > 0

    def test_general_metric_error(
        self, middleware, tool_specs, basic_messages, basic_tool_call
    ):
        """Test error in general semantic metric."""
        mock_metric = SemanticMetricResult(
            metric_name="general_hallucination_check",
            jsonschema={},
            prompt="test prompt",
            raw_response={},
            numeric_thresholds_checks={},
            is_important=True,
            importance_reason=None,
            error="JSON parsing failed: Invalid response format",
            is_correct=False,
            is_issue=False,
        )

        mock_pipeline_result = PipelineResult(
            inputs=FunctionCallInput(
                conversation_context=basic_messages,
                tools_inventory=tool_specs,
                tool_call=basic_tool_call,
            ),
            static=None,
            semantic=SemanticResult(
                function_selection=None,
                general=SemanticCategoryResult(
                    metrics={"general_hallucination_check": mock_metric},
                    final_decision=False,
                ),
                parameter=None,
                transform=None,
            ),
            overall_valid=False,
        )

        run_input = SPARCReflectionRunInput(
            messages=basic_messages,
            tool_specs=tool_specs,
            tool_calls=[basic_tool_call],
        )

        with patch.object(
            middleware._pipeline, "run_sync", return_value=mock_pipeline_result
        ):
            result = middleware.process(run_input, phase=AgentPhase.RUNTIME)

        assert result.output.reflection_result.decision == SPARCReflectionDecision.ERROR
        assert len(result.output.reflection_result.issues) > 0

    def test_parameter_metric_error(
        self, middleware, tool_specs, basic_messages, basic_tool_call
    ):
        """Test error in parameter-level metric."""
        mock_metric = SemanticMetricResult(
            metric_name="parameter_hallucination_check",
            jsonschema={},
            prompt="test prompt",
            raw_response={},
            numeric_thresholds_checks={},
            is_important=True,
            importance_reason=None,
            error="Model unavailable: Service temporarily unavailable",
            is_correct=False,
            is_issue=False,
        )

        mock_param_metrics = SemanticCategoryResult(
            metrics={"parameter_hallucination_check": mock_metric},
            final_decision=False,
        )

        mock_pipeline_result = PipelineResult(
            inputs=FunctionCallInput(
                conversation_context=basic_messages,
                tools_inventory=tool_specs,
                tool_call=basic_tool_call,
            ),
            static=None,
            semantic=SemanticResult(
                function_selection=None,
                general=None,
                parameter={"location": mock_param_metrics},
                transform=None,
            ),
            overall_valid=False,
        )

        run_input = SPARCReflectionRunInput(
            messages=basic_messages,
            tool_specs=tool_specs,
            tool_calls=[basic_tool_call],
        )

        with patch.object(
            middleware._pipeline, "run_sync", return_value=mock_pipeline_result
        ):
            result = middleware.process(run_input, phase=AgentPhase.RUNTIME)

        assert result.output.reflection_result.decision == SPARCReflectionDecision.ERROR
        assert len(result.output.reflection_result.issues) > 0

    def test_transformation_error(
        self, middleware, tool_specs, basic_messages, basic_tool_call
    ):
        """Test error in transformation execution."""
        mock_transform_info = TransformResult(
            units={"user_units": "km", "spec_units": "m", "user_value": 5},
            generated_code="result = value * 1000",
            execution_success=False,
            correct=False,
            execution_output=None,
            correction=None,
            error="Code execution failed: Division by zero in transformation",
        )

        mock_pipeline_result = PipelineResult(
            inputs=FunctionCallInput(
                conversation_context=basic_messages,
                tools_inventory=tool_specs,
                tool_call=basic_tool_call,
            ),
            static=None,
            semantic=SemanticResult(
                function_selection=None,
                general=None,
                parameter=None,
                transform={"location": mock_transform_info},
            ),
            overall_valid=False,
        )

        run_input = SPARCReflectionRunInput(
            messages=basic_messages,
            tool_specs=tool_specs,
            tool_calls=[basic_tool_call],
        )

        with patch.object(
            middleware._pipeline, "run_sync", return_value=mock_pipeline_result
        ):
            result = middleware.process(run_input, phase=AgentPhase.RUNTIME)

        assert result.output.reflection_result.decision == SPARCReflectionDecision.ERROR
        assert len(result.output.reflection_result.issues) > 0

    def test_mixed_errors_and_issues(
        self, middleware, tool_specs, basic_messages, basic_tool_call
    ):
        """Test scenario with both errors and validation issues."""
        # Create metric with error
        error_metric = SemanticMetricResult(
            metric_name="general_hallucination_check",
            jsonschema={},
            prompt="test prompt",
            raw_response={},
            numeric_thresholds_checks={},
            is_important=True,
            importance_reason=None,
            error="LLM timeout",
            is_correct=False,
            is_issue=False,
        )

        # Create metric with error (not a validation issue)
        issue_metric = SemanticMetricResult(
            metric_name="function_selection_appropriateness",
            jsonschema={},
            prompt="test prompt",
            raw_response={},
            numeric_thresholds_checks={},
            is_important=True,
            importance_reason=None,
            error="Function selection error: Invalid function chosen",
            is_correct=False,
            is_issue=False,
        )

        mock_pipeline_result = PipelineResult(
            inputs=FunctionCallInput(
                conversation_context=basic_messages,
                tools_inventory=tool_specs,
                tool_call=basic_tool_call,
            ),
            static=None,
            semantic=SemanticResult(
                function_selection=SemanticCategoryResult(
                    metrics={"function_selection_appropriateness": issue_metric},
                    final_decision=False,
                ),
                general=SemanticCategoryResult(
                    metrics={"general_hallucination_check": error_metric},
                    final_decision=False,
                ),
                parameter=None,
                transform=None,
            ),
            overall_valid=False,
        )

        run_input = SPARCReflectionRunInput(
            messages=basic_messages,
            tool_specs=tool_specs,
            tool_calls=[basic_tool_call],
        )

        with patch.object(
            middleware._pipeline, "run_sync", return_value=mock_pipeline_result
        ):
            result = middleware.process(run_input, phase=AgentPhase.RUNTIME)

        # ERROR should take precedence over REJECT when both errors and issues exist
        assert result.output.reflection_result.decision == SPARCReflectionDecision.ERROR
        assert len(result.output.reflection_result.issues) >= 2

    def test_multiple_errors_in_different_stages(
        self, middleware, tool_specs, basic_messages, basic_tool_call
    ):
        """Test multiple errors across different validation stages."""
        error_metric_1 = SemanticMetricResult(
            metric_name="general_hallucination_check",
            jsonschema={},
            prompt="test prompt",
            raw_response={},
            numeric_thresholds_checks={},
            is_important=True,
            importance_reason=None,
            error="Error 1: LLM timeout",
            is_correct=False,
            is_issue=False,
        )

        error_metric_2 = SemanticMetricResult(
            metric_name="parameter_hallucination_check",
            jsonschema={},
            prompt="test prompt",
            raw_response={},
            numeric_thresholds_checks={},
            is_important=True,
            importance_reason=None,
            error="Error 2: Invalid response format",
            is_correct=False,
            is_issue=False,
        )

        mock_param_metrics = SemanticCategoryResult(
            metrics={"parameter_hallucination_check": error_metric_2},
            final_decision=False,
        )

        mock_pipeline_result = PipelineResult(
            inputs=FunctionCallInput(
                conversation_context=basic_messages,
                tools_inventory=tool_specs,
                tool_call=basic_tool_call,
            ),
            static=None,
            semantic=SemanticResult(
                function_selection=None,
                general=SemanticCategoryResult(
                    metrics={"general_hallucination_check": error_metric_1},
                    final_decision=False,
                ),
                parameter={"location": mock_param_metrics},
                transform=None,
            ),
            overall_valid=False,
        )

        run_input = SPARCReflectionRunInput(
            messages=basic_messages,
            tool_specs=tool_specs,
            tool_calls=[basic_tool_call],
        )

        with patch.object(
            middleware._pipeline, "run_sync", return_value=mock_pipeline_result
        ):
            result = middleware.process(run_input, phase=AgentPhase.RUNTIME)

        assert result.output.reflection_result.decision == SPARCReflectionDecision.ERROR
        # Should have issues for both errors
        assert len(result.output.reflection_result.issues) >= 2

    def test_no_exception_on_error(
        self, middleware, tool_specs, basic_messages, basic_tool_call
    ):
        """Test that errors are handled gracefully without raising exceptions."""
        mock_metric = SemanticMetricResult(
            metric_name="general_hallucination_check",
            jsonschema={},
            prompt="test prompt",
            raw_response={},
            numeric_thresholds_checks={},
            is_important=True,
            importance_reason=None,
            error="Critical LLM failure",
            is_correct=False,
            is_issue=False,
        )

        mock_pipeline_result = PipelineResult(
            inputs=FunctionCallInput(
                conversation_context=basic_messages,
                tools_inventory=tool_specs,
                tool_call=basic_tool_call,
            ),
            static=None,
            semantic=SemanticResult(
                function_selection=None,
                general=SemanticCategoryResult(
                    metrics={"general_hallucination_check": mock_metric},
                    final_decision=False,
                ),
                parameter=None,
                transform=None,
            ),
            overall_valid=False,
        )

        run_input = SPARCReflectionRunInput(
            messages=basic_messages,
            tool_specs=tool_specs,
            tool_calls=[basic_tool_call],
        )

        # Should not raise any exception
        with patch.object(
            middleware._pipeline, "run_sync", return_value=mock_pipeline_result
        ):
            result = middleware.process(run_input, phase=AgentPhase.RUNTIME)

        assert result.output.reflection_result.decision == SPARCReflectionDecision.ERROR

    def test_error_messages_are_informative(
        self, middleware, tool_specs, basic_messages, basic_tool_call
    ):
        """Test that error messages contain useful debugging information."""
        error_message = (
            "LLM API Error: Rate limit exceeded - Please try again in 60 seconds"
        )

        mock_metric = SemanticMetricResult(
            metric_name="function_selection_appropriateness",
            jsonschema={},
            prompt="test prompt",
            raw_response={},
            numeric_thresholds_checks={},
            is_important=True,
            importance_reason=None,
            error=error_message,
            is_correct=False,
            is_issue=False,
        )

        mock_pipeline_result = PipelineResult(
            inputs=FunctionCallInput(
                conversation_context=basic_messages,
                tools_inventory=tool_specs,
                tool_call=basic_tool_call,
            ),
            static=None,
            semantic=SemanticResult(
                function_selection=SemanticCategoryResult(
                    metrics={"function_selection_appropriateness": mock_metric},
                    final_decision=False,
                ),
                general=None,
                parameter=None,
                transform=None,
            ),
            overall_valid=False,
        )

        run_input = SPARCReflectionRunInput(
            messages=basic_messages,
            tool_specs=tool_specs,
            tool_calls=[basic_tool_call],
        )

        with patch.object(
            middleware._pipeline, "run_sync", return_value=mock_pipeline_result
        ):
            result = middleware.process(run_input, phase=AgentPhase.RUNTIME)

        assert result.output.reflection_result.decision == SPARCReflectionDecision.ERROR

        # Check that error message is included in issues
        error_found = False
        for issue in result.output.reflection_result.issues:
            if "Rate limit exceeded" in issue.explanation:
                error_found = True
                break

        assert error_found, "Error message not found in issues"
