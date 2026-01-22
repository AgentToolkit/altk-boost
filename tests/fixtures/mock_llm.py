"""Mock LLM client for testing without making real API calls."""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, Union

from altk.core.llm import register_llm
from altk.core.llm.base import BaseLLMClient
from altk.core.llm.types import GenerationArgs, GenerationMode, LLMResponse


@dataclass
class CallRecord:
    """Records a single LLM call for verification in tests."""

    prompt: Union[str, List[Dict[str, Any]]]
    mode: GenerationMode
    generation_args: Optional[GenerationArgs]
    kwargs: Dict[str, Any]
    response: Union[str, LLMResponse]
    timestamp: float = field(default_factory=time.time)


class ResponseStrategy(ABC):
    """Abstract base class for response generation strategies."""

    @abstractmethod
    def get_response(
        self, prompt: Any, mode: GenerationMode, **kwargs: Any
    ) -> Union[str, LLMResponse]:
        """
        Generate a response based on the prompt and kwargs.

        Args:
            prompt: The input prompt (string or messages list)
            mode: The generation mode
            **kwargs: Additional arguments passed to generate

        Returns:
            Response string or LLMResponse object
        """
        pass

    def reset(self) -> None:  # noqa: B027
        """Reset strategy state (optional, for stateful strategies)."""
        pass


class StaticResponseStrategy(ResponseStrategy):
    """Returns predefined responses in sequence."""

    def __init__(self, responses: List[Union[str, LLMResponse]]):
        """
        Initialize with a list of responses.

        Args:
            responses: List of responses to return in order

        Raises:
            ValueError: If responses list is empty
        """
        if not responses:
            raise ValueError("responses list cannot be empty")
        self.responses = responses
        self.index = 0

    def get_response(
        self, prompt: Any, mode: GenerationMode, **kwargs: Any
    ) -> Union[str, LLMResponse]:
        """Return the next response in sequence."""
        if self.index >= len(self.responses):
            raise ValueError(
                f"No more responses configured (called {self.index + 1} times, "
                f"but only {len(self.responses)} responses provided)"
            )
        response = self.responses[self.index]
        self.index += 1
        return response

    def reset(self) -> None:
        """Reset to the first response."""
        self.index = 0


class CallbackResponseStrategy(ResponseStrategy):
    """Generates responses using a callback function."""

    def __init__(
        self,
        callback: Callable[
            [Any, GenerationMode, Dict[str, Any]], Union[str, LLMResponse]
        ],
    ):
        """
        Initialize with a callback function.

        Args:
            callback: Function that takes (prompt, mode, kwargs) and returns a response
        """
        self.callback = callback

    def get_response(
        self, prompt: Any, mode: GenerationMode, **kwargs: Any
    ) -> Union[str, LLMResponse]:
        """Generate response using the callback."""
        return self.callback(prompt, mode, kwargs)


class EchoResponseStrategy(ResponseStrategy):
    """Echoes the prompt back (useful for debugging)."""

    def __init__(self, prefix: str = "Echo: "):
        """
        Initialize echo strategy.

        Args:
            prefix: Prefix to add before echoed content
        """
        self.prefix = prefix

    def get_response(
        self, prompt: Any, mode: GenerationMode, **kwargs: Any
    ) -> Union[str, LLMResponse]:
        """Echo the prompt back with a prefix."""
        if isinstance(prompt, str):
            return f"{self.prefix}{prompt}"
        elif isinstance(prompt, list) and len(prompt) > 0:
            # Extract content from last message
            last_message = prompt[-1]
            content = last_message.get("content", "")
            return f"{self.prefix}{content}"
        return f"{self.prefix}<unknown prompt format>"


@register_llm("mock")
class MockLLMClient(BaseLLMClient):
    """
    Mock LLM client for testing that doesn't make real API calls.

    Features:
    - Configurable response strategies
    - Call recording for verification
    - Simulated delays
    - Error injection
    - Full async/sync support

    Example:
        >>> mock = MockLLMClient(responses=["Response 1", "Response 2"])
        >>> result = mock.generate("Test prompt")
        >>> assert result == "Response 1"
        >>> mock.assert_called_once()
    """

    def __init__(
        self,
        responses: Optional[List[Union[str, LLMResponse]]] = None,
        strategy: Optional[ResponseStrategy] = None,
        simulate_delay: float = 0.0,
        error_on_call: Optional[int] = None,
        error_type: Type[Exception] = RuntimeError,
        error_message: str = "Simulated LLM error",
        **kwargs: Any,
    ):
        """
        Initialize mock LLM client.

        Args:
            responses: List of responses to return in sequence (creates StaticResponseStrategy)
            strategy: Custom response strategy (overrides responses)
            simulate_delay: Delay in seconds to simulate API latency
            error_on_call: Raise error on this call number (0-indexed)
            error_type: Type of exception to raise
            error_message: Error message for the exception
            **kwargs: Additional arguments (e.g., hooks)
        """
        # Don't call super().__init__ as we don't need a real client
        self._hooks = kwargs.get("hooks", [])
        self._method_configs: Dict[str, Any] = {}
        self._parameter_mapper = None
        self._client = None  # Mock doesn't need a real client

        # Set up response strategy
        if strategy:
            self.strategy = strategy
        elif responses:
            self.strategy = StaticResponseStrategy(responses)
        else:
            self.strategy = EchoResponseStrategy()

        # Configuration
        self.simulate_delay = simulate_delay
        self.error_on_call = error_on_call
        self.error_type = error_type
        self.error_message = error_message

        # Call tracking
        self.call_history: List[CallRecord] = []
        self.call_count = 0

        # Register methods
        self._register_methods()

    @classmethod
    def provider_class(cls) -> Type[Any]:
        """Return mock provider class."""
        return type("MockProvider", (), {})

    def _register_methods(self) -> None:
        """Register mock method configurations."""
        # These are dummy configs since we override _generate
        from altk.core.llm.base import MethodConfig

        self._method_configs["text"] = MethodConfig("generate", "prompt")
        self._method_configs["chat"] = MethodConfig("generate", "messages")
        self._method_configs["text_async"] = MethodConfig("generate_async", "prompt")
        self._method_configs["chat_async"] = MethodConfig("generate_async", "messages")

    def _setup_parameter_mapper(self) -> None:
        """No parameter mapping needed for mock."""
        pass

    def _parse_llm_response(self, raw: Any) -> Union[str, LLMResponse]:
        """Mock responses are already parsed."""
        return raw

    def _check_error_injection(self) -> None:
        """Check if we should inject an error."""
        if self.error_on_call is not None and self.call_count == self.error_on_call:
            raise self.error_type(self.error_message)

    def _simulate_delay(self) -> None:
        """Simulate API latency if configured."""
        if self.simulate_delay > 0:
            time.sleep(self.simulate_delay)

    async def _simulate_delay_async(self) -> None:
        """Simulate API latency asynchronously if configured."""
        if self.simulate_delay > 0:
            await asyncio.sleep(self.simulate_delay)

    def _generate(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        mode: Union[str, GenerationMode] = GenerationMode.CHAT,
        generation_args: Optional[GenerationArgs] = None,
        **kwargs: Any,
    ) -> Union[str, LLMResponse]:
        """Generate mock response synchronously."""
        self._check_error_injection()
        self._simulate_delay()

        # Convert mode to enum if needed
        if isinstance(mode, str):
            mode = GenerationMode(mode)

        # Get response from strategy
        response = self.strategy.get_response(prompt, mode, **kwargs)

        # Record the call
        record = CallRecord(
            prompt=prompt,
            mode=mode,
            generation_args=generation_args,
            kwargs=kwargs,
            response=response,
        )
        self.call_history.append(record)
        self.call_count += 1

        # Emit hooks
        self._emit(
            "before_generate",
            {"mode": mode.value, "args": {"prompt": prompt, **kwargs}},
        )
        self._emit("after_generate", {"mode": mode.value, "response": response})

        return response

    async def _generate_async(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        *,
        mode: Union[str, GenerationMode] = GenerationMode.CHAT_ASYNC,
        generation_args: Optional[GenerationArgs] = None,
        **kwargs: Any,
    ) -> Union[str, LLMResponse]:
        """Generate mock response asynchronously."""
        self._check_error_injection()
        await self._simulate_delay_async()

        # Convert mode to enum if needed
        if isinstance(mode, str):
            mode = GenerationMode(mode)

        # Get response from strategy
        response = self.strategy.get_response(prompt, mode, **kwargs)

        # Record the call
        record = CallRecord(
            prompt=prompt,
            mode=mode,
            generation_args=generation_args,
            kwargs=kwargs,
            response=response,
        )
        self.call_history.append(record)
        self.call_count += 1

        # Emit hooks
        self._emit(
            "before_generate_async",
            {"mode": mode.value, "args": {"prompt": prompt, **kwargs}},
        )
        self._emit("after_generate_async", {"mode": mode.value, "response": response})

        return response

    # Public API methods
    def generate(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        mode: Union[str, GenerationMode] = GenerationMode.CHAT,
        generation_args: Optional[GenerationArgs] = None,
        **kwargs: Any,
    ) -> Union[str, LLMResponse]:
        """
        Generate a response synchronously.

        Args:
            prompt: The input prompt (string or messages list)
            mode: Generation mode (default: CHAT)
            generation_args: Optional generation arguments
            **kwargs: Additional provider-specific arguments

        Returns:
            Generated response (string or LLMResponse)
        """
        return self._generate(prompt, mode, generation_args, **kwargs)

    async def generate_async(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        *,
        mode: Union[str, GenerationMode] = GenerationMode.CHAT_ASYNC,
        generation_args: Optional[GenerationArgs] = None,
        **kwargs: Any,
    ) -> Union[str, LLMResponse]:
        """
        Generate a response asynchronously.

        Args:
            prompt: The input prompt (string or messages list)
            mode: Generation mode (default: CHAT_ASYNC)
            generation_args: Optional generation arguments
            **kwargs: Additional provider-specific arguments

        Returns:
            Generated response (string or LLMResponse)
        """
        return await self._generate_async(
            prompt, mode=mode, generation_args=generation_args, **kwargs
        )

    # Verification helpers
    def assert_called(self) -> None:
        """Assert that the mock was called at least once."""
        assert self.call_count > 0, "Mock LLM was never called"

    def assert_called_once(self) -> None:
        """Assert that the mock was called exactly once."""
        assert self.call_count == 1, f"Expected 1 call, got {self.call_count}"

    def assert_called_n_times(self, n: int) -> None:
        """Assert that the mock was called exactly n times."""
        assert self.call_count == n, f"Expected {n} calls, got {self.call_count}"

    def assert_called_with(
        self,
        prompt: Optional[Union[str, List[Dict[str, Any]]]] = None,
        mode: Optional[GenerationMode] = None,
        **kwargs: Any,
    ) -> None:
        """
        Assert the last call had specific arguments.

        Args:
            prompt: Expected prompt (optional)
            mode: Expected generation mode (optional)
            **kwargs: Expected keyword arguments (optional)

        Raises:
            AssertionError: If assertions fail
        """
        assert self.call_count > 0, "Mock LLM was never called"
        last_call = self.call_history[-1]

        if prompt is not None:
            assert last_call.prompt == prompt, (
                f"Expected prompt {prompt}, got {last_call.prompt}"
            )
        if mode is not None:
            assert last_call.mode == mode, f"Expected mode {mode}, got {last_call.mode}"
        for key, value in kwargs.items():
            assert key in last_call.kwargs, f"Argument {key} not found in call"
            assert last_call.kwargs[key] == value, (
                f"Expected {key}={value}, got {last_call.kwargs[key]}"
            )

    def assert_any_call_with(
        self,
        prompt: Optional[Union[str, List[Dict[str, Any]]]] = None,
        mode: Optional[GenerationMode] = None,
        **kwargs: Any,
    ) -> None:
        """
        Assert that at least one call had specific arguments.

        Args:
            prompt: Expected prompt (optional)
            mode: Expected generation mode (optional)
            **kwargs: Expected keyword arguments (optional)

        Raises:
            AssertionError: If no matching call is found
        """
        assert self.call_count > 0, "Mock LLM was never called"

        for call in self.call_history:
            matches = True
            if prompt is not None and call.prompt != prompt:
                matches = False
            if mode is not None and call.mode != mode:
                matches = False
            for key, value in kwargs.items():
                if key not in call.kwargs or call.kwargs[key] != value:
                    matches = False
            if matches:
                return

        raise AssertionError(
            f"No call found matching criteria: prompt={prompt}, mode={mode}, kwargs={kwargs}"
        )

    def get_call(self, index: int) -> CallRecord:
        """
        Get a specific call record by index.

        Args:
            index: Index of the call (0-based)

        Returns:
            CallRecord for the specified call

        Raises:
            IndexError: If index is out of range
        """
        return self.call_history[index]

    def get_last_call(self) -> CallRecord:
        """
        Get the most recent call record.

        Returns:
            CallRecord for the last call

        Raises:
            IndexError: If no calls have been made
        """
        if not self.call_history:
            raise IndexError("No calls have been made")
        return self.call_history[-1]

    def reset(self) -> None:
        """Reset call history, counter, and strategy state."""
        self.call_history.clear()
        self.call_count = 0
        self.strategy.reset()
