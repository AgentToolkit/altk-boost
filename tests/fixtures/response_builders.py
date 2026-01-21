"""Utilities for building mock LLM responses."""

import json
from typing import Any, Dict, List, Optional

from altk.core.llm.types import LLMResponse


class ResponseBuilder:
    """Builder for creating mock LLM responses of various types."""

    @staticmethod
    def simple(text: str) -> str:
        """
        Create a simple text response.

        Args:
            text: The response text

        Returns:
            Plain text response string

        Example:
            >>> response = ResponseBuilder.simple("Hello, world!")
            >>> assert response == "Hello, world!"
        """
        return text

    @staticmethod
    def structured(
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Create a structured LLMResponse object.

        Args:
            content: The response content
            tool_calls: Optional list of tool calls

        Returns:
            LLMResponse object

        Example:
            >>> response = ResponseBuilder.structured("Test response")
            >>> assert isinstance(response, LLMResponse)
            >>> assert response.content == "Test response"
        """
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
        )

    @staticmethod
    def tool_call(
        tool_name: str,
        arguments: Dict[str, Any],
        content: Optional[str] = None,
        call_id: Optional[str] = None,
    ) -> LLMResponse:
        """
        Create a response with tool calls.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool call
            content: Optional text content alongside tool call
            call_id: Optional custom call ID (defaults to "call_{tool_name}")

        Returns:
            LLMResponse with tool calls

        Example:
            >>> response = ResponseBuilder.tool_call(
            ...     "get_weather",
            ...     {"city": "San Francisco"}
            ... )
            >>> assert response.tool_calls[0]["function"]["name"] == "get_weather"
        """
        if call_id is None:
            call_id = f"call_{tool_name}"

        return LLMResponse(
            content=content or "",
            tool_calls=[
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": json.dumps(arguments)},
                }
            ],
        )

    @staticmethod
    def multiple_tool_calls(
        tool_calls: List[Dict[str, Any]], content: Optional[str] = None
    ) -> LLMResponse:
        """
        Create a response with multiple tool calls.

        Args:
            tool_calls: List of dicts with 'name' and 'arguments' keys
            content: Optional text content alongside tool calls

        Returns:
            LLMResponse with multiple tool calls

        Example:
            >>> response = ResponseBuilder.multiple_tool_calls([
            ...     {"name": "get_weather", "arguments": {"city": "SF"}},
            ...     {"name": "get_time", "arguments": {"timezone": "PST"}}
            ... ])
            >>> assert len(response.tool_calls) == 2
        """
        formatted_calls = []
        for i, call in enumerate(tool_calls):
            formatted_calls.append(
                {
                    "id": f"call_{call['name']}_{i}",
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call["arguments"]),
                    },
                }
            )

        return LLMResponse(
            content=content or "",
            tool_calls=formatted_calls,
        )

    @staticmethod
    def json(data: Dict[str, Any], pretty: bool = True) -> str:
        """
        Create a JSON response.

        Args:
            data: Dictionary to serialize as JSON
            pretty: Whether to pretty-print the JSON (default: True)

        Returns:
            JSON string

        Example:
            >>> response = ResponseBuilder.json({"status": "success"})
            >>> assert "success" in response
        """
        if pretty:
            return json.dumps(data, indent=2)
        return json.dumps(data)

    @staticmethod
    def error_response(error_message: str, error_type: str = "Error") -> str:
        """
        Create an error response.

        Args:
            error_message: The error message
            error_type: Type of error (default: "Error")

        Returns:
            Formatted error string

        Example:
            >>> response = ResponseBuilder.error_response("Connection failed")
            >>> assert "Error" in response
        """
        return f"{error_type}: {error_message}"

    @staticmethod
    def multi_turn(responses: List[str]) -> List[str]:
        """
        Create multiple responses for multi-turn conversations.

        Args:
            responses: List of response strings

        Returns:
            List of responses (for use with StaticResponseStrategy)

        Example:
            >>> responses = ResponseBuilder.multi_turn(["Hi", "How are you?", "Goodbye"])
            >>> assert len(responses) == 3
        """
        return responses

    @staticmethod
    def streaming_chunk(
        content: str, index: int = 0, finish_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a streaming response chunk.

        Args:
            content: Content for this chunk
            index: Chunk index
            finish_reason: Optional finish reason for final chunk

        Returns:
            Dictionary representing a streaming chunk

        Example:
            >>> chunk = ResponseBuilder.streaming_chunk("Hello", index=0)
            >>> assert chunk["choices"][0]["delta"]["content"] == "Hello"
        """
        return {
            "id": f"chatcmpl-mock-{index}",
            "object": "chat.completion.chunk",
            "created": 1234567890,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": content} if content else {},
                    "finish_reason": finish_reason,
                }
            ],
        }

    @staticmethod
    def code_block(code: str, language: str = "python") -> str:
        """
        Create a response with a code block.

        Args:
            code: The code content
            language: Programming language for syntax highlighting

        Returns:
            Markdown-formatted code block

        Example:
            >>> response = ResponseBuilder.code_block("print('hello')", "python")
            >>> assert "```python" in response
        """
        return f"```{language}\n{code}\n```"

    @staticmethod
    def markdown(content: str, title: Optional[str] = None) -> str:
        """
        Create a markdown-formatted response.

        Args:
            content: Markdown content
            title: Optional title (will be formatted as H1)

        Returns:
            Markdown-formatted string

        Example:
            >>> response = ResponseBuilder.markdown("Content", title="Title")
            >>> assert "# Title" in response
        """
        if title:
            return f"# {title}\n\n{content}"
        return content

    @staticmethod
    def list_items(items: List[str], ordered: bool = False) -> str:
        """
        Create a response with a list of items.

        Args:
            items: List of items
            ordered: Whether to use ordered list (default: False for bullet points)

        Returns:
            Markdown-formatted list

        Example:
            >>> response = ResponseBuilder.list_items(["Item 1", "Item 2"])
            >>> assert "- Item 1" in response
        """
        if ordered:
            return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
        return "\n".join(f"- {item}" for item in items)

    @staticmethod
    def table(headers: List[str], rows: List[List[str]]) -> str:
        """
        Create a markdown table response.

        Args:
            headers: Column headers
            rows: List of rows (each row is a list of cell values)

        Returns:
            Markdown-formatted table

        Example:
            >>> response = ResponseBuilder.table(
            ...     ["Name", "Age"],
            ...     [["Alice", "30"], ["Bob", "25"]]
            ... )
            >>> assert "| Name | Age |" in response
        """
        # Header row
        table = "| " + " | ".join(headers) + " |\n"
        # Separator row
        table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        # Data rows
        for row in rows:
            table += "| " + " | ".join(row) + " |\n"
        return table.rstrip()
