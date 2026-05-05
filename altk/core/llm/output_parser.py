import re
import json
from abc import ABC, abstractmethod
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

import jsonschema

from pydantic import (
    BaseModel,
    create_model,
    Field,
    ValidationError as PydanticValidationError,
)

from .base import BaseLLMClient

T = TypeVar("T")


def json_schema_to_pydantic_model(
    schema: Dict[str, Any],
    model_name: str = "AutoModel",
    free_form_object_as_str: bool = False,
) -> Type[BaseModel]:
    """Build a Pydantic model from a JSON Schema dict.

    Args:
        schema: JSON Schema dict.
        model_name: name of the generated Pydantic model.
        free_form_object_as_str: when ``True``, any free-form ``type: object``
            property (one without its own ``properties`` sub-schema) is
            modeled as a JSON-formatted ``str`` instead of a ``dict``. This
            is the workaround for OpenAI's structured-output API, which
            requires ``additionalProperties: false`` on every object schema —
            a constraint that free-form dicts cannot meet. The caller is
            expected to use :func:`relax_freeform_object_schema` when
            validating the raw output so the JSON-string form is accepted.
            Default ``False`` preserves backward-compatible behavior.
    """
    fields = {}
    required_fields = set(schema.get("required", []))

    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }

    def _map_object_for_prop(prop_schema: Dict[str, Any]) -> Type:
        """Return dict/str for a property whose declared type is ``object``.

        A property is "free-form" if it has no ``properties`` sub-schema; the
        OpenAI workaround only applies to those.
        """
        if free_form_object_as_str and "properties" not in prop_schema:
            return str
        return dict

    def parse_type(
        type_def: Union[str, List[str], None],
        prop_schema: Dict[str, Any],
    ) -> Type[T]:
        def _lookup(t: str) -> Type:
            return _map_object_for_prop(prop_schema) if t == "object" else type_mapping.get(t, Any)

        if isinstance(type_def, list):
            python_types = [_lookup(t) for t in type_def]
            if type(None) in python_types:
                python_types.remove(type(None))
                if len(python_types) == 1:
                    return Optional[python_types[0]]  # type: ignore
                else:
                    return Optional[Union[tuple(python_types)]]  # type: ignore
            else:
                return Union[tuple(python_types)]  # type: ignore
        if isinstance(type_def, str):
            return _lookup(type_def)
        return Any  # type: ignore[return-value]

    for prop_name, prop_schema in schema.get("properties", {}).items():
        field_type: Any = parse_type(prop_schema.get("type"), prop_schema)
        default = ... if prop_name in required_fields else None
        description = prop_schema.get("description", None)
        field_args = {"description": description} if description else {}
        fields[prop_name] = (field_type, Field(default, **field_args))

    return create_model(model_name, **fields)  # type: ignore


def relax_freeform_object_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep copy of *schema* with free-form ``"type": "object"``
    properties widened to accept ``"string"`` as well.

    This is the validation-time counterpart to
    ``json_schema_to_pydantic_model(..., free_form_object_as_str=True)``: when
    the Pydantic model emits a JSON string for a free-form object field,
    ``jsonschema.validate`` against the original schema would reject it. This
    helper widens those fields so the same schema accepts both object-literal
    and stringified forms. Schemas where the object has sub-``properties`` are
    left alone.
    """
    import copy

    relaxed = copy.deepcopy(schema)
    for _prop, prop_schema in relaxed.get("properties", {}).items():
        t = prop_schema.get("type")
        if t == "object" and "properties" not in prop_schema:
            prop_schema["type"] = ["object", "string"]
    return relaxed


class OutputValidationError(Exception):
    """Raised when LLM output cannot be validated against the provided schema."""


class ValidatingLLMClient(BaseLLMClient, ABC):
    """
    An LLMClient wrapper enforcing output structure via:
      - JSON Schema (dict),
      - Pydantic model (BaseModel subclass),
      - or Python built-in types (int, float, str, bool, list, dict).

    Features:
      - Injects a system-level prompt describing the required format.
      - Cleans raw responses (strips Markdown, extracts JSON).
      - Validates and parses the response.
      - Retries only invalid items (single or batch) up to `retries` times.
      - Falls back to single-item loops if no batch method is configured.

    Production knobs (instance-level, with class-level defaults):
      - ``free_form_object_as_str``: when ``True``, free-form ``type: object``
        schema fields are modeled in Pydantic as ``str`` (and the validation
        schema is widened at runtime to accept both object and string). Use
        this for providers that require ``additionalProperties: false`` on
        every object schema (notably OpenAI's structured-output API).
      - ``prompt_based_validation``: when ``True``, the schema is always
        injected into the system prompt and no native ``response_format``
        kwarg is forwarded. Use for providers that don't support OpenAI-style
        structured output (e.g. watsonx).
      - ``default_generation_kwargs``: dict of kwargs merged into every
        ``generate``/``generate_async`` call (e.g. ``{"max_tokens": 8096,
        "temperature": 0}``). Caller-provided kwargs override the defaults.
    """

    # Class-level defaults — override on subclasses or per instance in
    # ``configure_validation`` / constructor kwargs.
    free_form_object_as_str: bool = False
    prompt_based_validation: bool = False

    def __init__(
        self,
        *,
        free_form_object_as_str: Optional[bool] = None,
        prompt_based_validation: Optional[bool] = None,
        default_generation_kwargs: Optional[Dict[str, Any]] = None,
        **base_kwargs: Any,
    ) -> None:
        if free_form_object_as_str is not None:
            self.free_form_object_as_str = free_form_object_as_str
        if prompt_based_validation is not None:
            self.prompt_based_validation = prompt_based_validation
        self.default_generation_kwargs: Dict[str, Any] = dict(
            default_generation_kwargs or {}
        )
        super().__init__(**base_kwargs)
        # Wrap the subclass's _parse_llm_response so empty / malformed LLM
        # outputs retry gracefully (the retry loop treats "" as invalid)
        # rather than raising an unrecoverable ValueError.
        # This particularly covers reasoning models that exhaust max_tokens
        # on "thinking" tokens and return finish_reason="length" with no
        # content but non-empty reasoning_content.
        orig_parse = self._parse_llm_response
        self._parse_llm_response = self._build_safe_parse(orig_parse)  # type: ignore[assignment]

    def configure_validation(
        self,
        *,
        free_form_object_as_str: Optional[bool] = None,
        prompt_based_validation: Optional[bool] = None,
        default_generation_kwargs: Optional[Dict[str, Any]] = None,
    ) -> "ValidatingLLMClient":
        """Update the validation knobs after construction (chainable)."""
        if free_form_object_as_str is not None:
            self.free_form_object_as_str = free_form_object_as_str
        if prompt_based_validation is not None:
            self.prompt_based_validation = prompt_based_validation
        if default_generation_kwargs is not None:
            self.default_generation_kwargs = dict(default_generation_kwargs)
        return self

    @staticmethod
    def _build_safe_parse(orig):  # noqa: ANN001, ANN205
        """Wrap ``_parse_llm_response`` so parse failures become retry-worthy
        empty strings instead of raising. Also surfaces a targeted warning
        when a reasoning-only response exhausted the token budget."""
        import logging as _logging

        _logger = _logging.getLogger("altk.core.llm.output_parser")

        def _safe_parse(raw):  # noqa: ANN001, ANN202
            try:
                return orig(raw)
            except (ValueError, KeyError):
                # Detect: choice with reasoning_content but finish_reason='length'
                _choices = getattr(raw, "choices", None) or (
                    raw.get("choices", []) if isinstance(raw, dict) else []
                )
                if _choices:
                    c0 = _choices[0]
                    _msg = getattr(c0, "message", None) or (
                        c0.get("message", {}) if isinstance(c0, dict) else {}
                    )
                    _reasoning = (
                        getattr(_msg, "reasoning_content", None)
                        or (
                            _msg.get("reasoning_content")
                            if isinstance(_msg, dict)
                            else None
                        )
                    )
                    _finish = getattr(c0, "finish_reason", None) or (
                        c0.get("finish_reason") if isinstance(c0, dict) else None
                    )
                    if _reasoning and _finish == "length":
                        _logger.warning(
                            "LLM reasoning consumed the entire token budget "
                            "(finish_reason='length'). Consider increasing "
                            "max_tokens. Will retry."
                        )
                        return ""
                _logger.debug("LLM returned empty/unparseable response; will retry.")
                return ""

        return _safe_parse

    @classmethod
    @abstractmethod
    def provider_class(cls) -> Type[Any]:
        """Return the underlying SDK client class, e.g. openai.OpenAI."""

    @abstractmethod
    def _register_methods(self) -> None:
        """
        Register MethodConfig entries:
          self.set_method_config("text", ...),
          self.set_method_config("chat", ...),
          self.set_method_config("text_async", ...),
          self.set_method_config("chat_async", ...),
        """

    def _make_instruction(
        self, schema: Union[Dict[str, Any], Type[BaseModel], Type[Any]]
    ) -> str:
        """Produce a clear instruction describing exactly the required output format."""
        if isinstance(schema, dict):
            schema_json = json.dumps(schema, indent=2)
            return (
                "Please output ONLY a JSON object conforming exactly to the following JSON Schema:\n"
                f"{schema_json}"
            )
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            model_schema = schema.model_json_schema()
            return (
                "Please output ONLY a JSON object conforming exactly to this Pydantic model schema:\n"
                f"{model_schema}"
            )
        if isinstance(schema, type) and schema in (int, float, str, bool, list, dict):
            # For simple types, no JSON wrapper required
            return f"Please output ONLY a value of type `{schema.__name__}`."
        raise TypeError(f"Unsupported schema type: {schema!r}")

    @staticmethod
    def _extract_json(raw: str) -> str:
        """
        Extract JSON from markdown fences or inline braces.
        Falls back to returning the entire raw string.
        """
        # Code fence (```json ... ```)
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
        if fence:
            return fence.group(1)
        # Inline {...}
        inline = re.search(r"(\{[\s\S]*\})", raw)
        if inline:
            return inline.group(1)
        return raw

    def _clean_raw(self, raw: str) -> str:
        """Strip extraneous markdown and whitespace."""
        cleaned = self._extract_json(raw)
        return cleaned.strip()

    def _validate(
        self, raw: str, schema: Union[Dict[str, Any], Type[BaseModel], Type[Any]]
    ) -> Any:
        """
        Clean, parse, and validate raw text against the schema/type.
        Returns the parsed object or Pydantic instance.
        Raises OutputValidationError on any failure.
        """

        cleaned = self._clean_raw(raw)
        try:
            if isinstance(schema, str):
                data = cleaned
            else:
                data = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                data = json.loads(cleaned.encode("unicode_escape").decode("utf-8"))
            except Exception:
                data = cleaned

        # JSON Schema validation
        if isinstance(schema, dict):
            if jsonschema is None:
                raise ImportError(
                    "jsonschema is required for JSON Schema validation. Install with: pip install jsonschema"
                )
            # Widen free-form object props to also accept strings when we're
            # configured to round-trip them as JSON strings (see
            # ``free_form_object_as_str`` in the class docstring).
            effective_schema = (
                relax_freeform_object_schema(schema)
                if self.free_form_object_as_str
                else schema
            )
            try:
                jsonschema.validate(instance=data, schema=effective_schema)
            except jsonschema.ValidationError as e:
                raise OutputValidationError(
                    f"JSON Schema validation error: {e.message}"
                ) from e
            return data

        # Pydantic model validation
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            try:
                return schema.model_validate(data)
            except PydanticValidationError as e:
                raise OutputValidationError(f"Pydantic validation error: {e}") from e

        # Built-in type enforcement
        if isinstance(schema, type) and schema in (int, float, str, bool, list, dict):
            if not isinstance(data, schema):
                raise OutputValidationError(
                    f"Type mismatch: expected {schema.__name__}, got {type(data).__name__}"
                )
            return data

        raise TypeError(f"Unsupported schema type: {schema!r}")

    def _inject_system(
        self, prompt: Union[str, List[Dict[str, Any]]], instr: str
    ) -> Union[str, List[Dict[str, Any]]]:
        """
        Combine instruction and user prompt:
        - For text: prepend the instruction.
        - For chat messages: if first role=system, append instr to it;
          otherwise insert a new system message.
        """
        if isinstance(prompt, str):
            return f"{instr}\n\n{prompt}"

        msgs = prompt.copy()
        if msgs and msgs[0].get("role") == "system":
            msgs[0]["content"] = msgs[0]["content"].rstrip() + "\n\n" + instr
        else:
            msgs.insert(0, {"role": "system", "content": instr})
        return msgs

    def generate(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        *,
        schema: Union[Dict[str, Any], Type[BaseModel], Type[Any]],
        schema_field: Optional[str] = None,
        retries: int = 3,
        include_schema_in_system_prompt: bool = False,
        **kwargs: Any,
    ) -> Union[str, Any]:
        """
        Synchronous single-item generation with validation + retries.
        """
        # Instance defaults — caller kwargs win.
        if self.default_generation_kwargs:
            merged = {**self.default_generation_kwargs}
            merged.update(kwargs)
            kwargs = merged
        # Providers that don't support native structured output switch to
        # prompt-based schema injection and drop any OpenAI-style
        # ``response_format`` field.
        if self.prompt_based_validation:
            include_schema_in_system_prompt = True
            schema_field = None
        current = prompt
        instr = None
        if include_schema_in_system_prompt:
            instr = self._make_instruction(schema)
            current = self._inject_system(prompt, instr)
        if schema_field:
            kwargs[schema_field] = schema
            if isinstance(schema, dict):
                new_schema = json_schema_to_pydantic_model(
                    schema,
                    free_form_object_as_str=self.free_form_object_as_str,
                )
                kwargs[schema_field] = new_schema

        last_error: Optional[str] = None
        for _ in range(1, retries + 1):
            # Filter out schema-related kwargs for the base class
            filtered_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k
                not in [
                    "schema",
                    "schema_field",
                    "retries",
                    "include_schema_in_system_prompt",
                ]
            }
            raw = super()._generate(**{"prompt": current, **filtered_kwargs})
            try:
                if isinstance(raw, str):
                    return self._validate(raw, schema)
                return raw
            except OutputValidationError as e:
                last_error = str(e)
                correction = (
                    f"The previous response did not conform: {last_error}\nPlease correct it."
                    " And remember to output ONLY the requested schema, without any additional text."
                )
                if isinstance(current, str):
                    if instr:
                        current = (
                            f"{instr}\n\nPrevious output:\n{raw}\n\n"
                            f"{correction}\n\n{prompt}"
                        )
                    else:
                        current = f"Previous output:\n{raw}\n\n{correction}\n\n{prompt}"
                else:
                    current = current + [
                        {"role": "assistant", "content": raw},
                        {"role": "user", "content": correction},
                    ]
        raise OutputValidationError(f"Failed after {retries} attempts: {last_error}")

    async def generate_async(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        *,
        schema: Union[Dict[str, Any], Type[BaseModel], Type[Any]],
        schema_field: Optional[str] = None,
        retries: int = 3,
        include_schema_in_system_prompt: bool = False,
        **kwargs: Any,
    ) -> Union[str, Any]:
        """
        Asynchronous single-item generation with validation + retries.
        """
        # Instance defaults — caller kwargs win.
        if self.default_generation_kwargs:
            merged = {**self.default_generation_kwargs}
            merged.update(kwargs)
            kwargs = merged
        # Providers that don't support native structured output switch to
        # prompt-based schema injection and drop any OpenAI-style
        # ``response_format`` field.
        if self.prompt_based_validation:
            include_schema_in_system_prompt = True
            schema_field = None
        current = prompt
        instr = None
        if include_schema_in_system_prompt:
            instr = self._make_instruction(schema)
            current = self._inject_system(prompt, instr)
        if schema_field:
            kwargs[schema_field] = schema
            if isinstance(schema, dict):
                new_schema = json_schema_to_pydantic_model(
                    schema,
                    free_form_object_as_str=self.free_form_object_as_str,
                )
                kwargs[schema_field] = new_schema

        last_error: Optional[str] = None
        for _ in range(1, retries + 1):
            # Filter out schema-related kwargs for the base class
            filtered_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k
                not in [
                    "schema",
                    "schema_field",
                    "retries",
                    "include_schema_in_system_prompt",
                ]
            }
            raw = await super()._generate_async(
                **{"prompt": current, **filtered_kwargs}
            )
            try:
                if isinstance(raw, str):
                    return self._validate(raw, schema)
                return raw
            except OutputValidationError as e:
                last_error = str(e)
                correction = (
                    f"The previous response did not conform: {last_error}\nPlease correct it."
                    " And remember to output ONLY the requested schema, without any additional text."
                )
                if isinstance(current, str):
                    if instr:
                        current = (
                            f"{instr}\n\nPrevious output:\n{raw}\n\n"
                            f"{correction}\n\n{prompt}"
                        )
                    else:
                        current = f"Previous output:\n{raw}\n\n{correction}\n\n{prompt}"
                else:
                    current = current + [
                        {"role": "assistant", "content": raw},
                        {"role": "user", "content": correction},
                    ]
        raise OutputValidationError(f"Failed after {retries} attempts: {last_error}")
