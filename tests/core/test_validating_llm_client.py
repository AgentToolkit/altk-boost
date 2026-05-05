"""Tests for ``ValidatingLLMClient`` production knobs.

Covers the behaviors migrated from CLEAR's monkey-patches:

- ``free_form_object_as_str`` changes how free-form ``type: object`` fields are
  modeled (as ``str`` in Pydantic) and loosens ``_validate`` to accept the
  stringified form. Together these make SPARC/CLEAR compatible with OpenAI's
  ``additionalProperties: false`` structured-output requirement.
- ``prompt_based_validation`` forces schema-into-system-prompt and skips
  native ``response_format``. Targeted at providers like watsonx.
- ``default_generation_kwargs`` forwards e.g. ``max_tokens``/``temperature``
  into every ``generate`` call, with caller kwargs winning.
- The wrapped ``_parse_llm_response`` returns ``""`` on parse error and
  warns when a reasoning-only response exhausted the budget.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Type

import pytest

from altk.core.llm.output_parser import (
    OutputValidationError,
    ValidatingLLMClient,
    json_schema_to_pydantic_model,
    relax_freeform_object_schema,
)

# ---------------------------------------------------------------------------
# Dummy client used throughout — no actual LLM call.
# ---------------------------------------------------------------------------


class _FakeValidating(ValidatingLLMClient):
    """Minimal concrete subclass — real ``_generate`` is stubbed via
    ``monkeypatch`` in each test, because ``super()._generate`` inside
    ``ValidatingLLMClient.generate`` bypasses subclass overrides."""

    @classmethod
    def provider_class(cls) -> Type[Any]:
        return object

    def _register_methods(self) -> None:  # noqa: D401
        pass

    def _setup_parameter_mapper(self) -> None:  # noqa: D401
        pass

    def _parse_llm_response(self, raw: Any) -> str:
        if isinstance(raw, Exception):
            raise raw
        return str(raw)

    def __init__(self, **kw):
        super().__init__(**kw)


def _install_scripted_generate(monkeypatch, observed: list, scripted: list):
    """Replace ``BaseLLMClient._generate`` so tests can intercept the call
    that happens inside ``ValidatingLLMClient.generate``'s retry loop."""
    from altk.core.llm.base import BaseLLMClient

    def fake_generate(self, **kwargs):  # noqa: ANN001
        observed.append(kwargs)
        if not scripted:
            return ""
        raw = scripted.pop(0)
        return self._parse_llm_response(raw)

    monkeypatch.setattr(BaseLLMClient, "_generate", fake_generate, raising=True)


# ---------------------------------------------------------------------------
# json_schema_to_pydantic_model — free_form_object_as_str
# ---------------------------------------------------------------------------


class TestJsonSchemaToPydantic:
    def test_default_keeps_object_as_dict(self):
        m = json_schema_to_pydantic_model(
            {"type": "object", "properties": {"a": {"type": "object"}}}
        )
        assert m.model_fields["a"].annotation is dict

    def test_freeform_object_flag_switches_to_str(self):
        m = json_schema_to_pydantic_model(
            {"type": "object", "properties": {"a": {"type": "object"}}},
            free_form_object_as_str=True,
        )
        assert m.model_fields["a"].annotation is str

    def test_freeform_flag_keeps_nested_objects_as_dict(self):
        # only free-form (no properties) converts; an object with properties
        # keeps its dict shape (OpenAI can still satisfy additionalProperties
        # when the sub-schema is fully specified).
        m = json_schema_to_pydantic_model(
            {
                "type": "object",
                "properties": {
                    "flat": {"type": "object"},
                    "structured": {
                        "type": "object",
                        "properties": {"x": {"type": "string"}},
                    },
                },
            },
            free_form_object_as_str=True,
        )
        assert m.model_fields["flat"].annotation is str
        assert m.model_fields["structured"].annotation is dict


# ---------------------------------------------------------------------------
# relax_freeform_object_schema
# ---------------------------------------------------------------------------


class TestRelaxFreeformObjectSchema:
    def test_relaxes_freeform_object(self):
        out = relax_freeform_object_schema(
            {"type": "object", "properties": {"a": {"type": "object"}}}
        )
        assert out["properties"]["a"]["type"] == ["object", "string"]

    def test_leaves_structured_objects_alone(self):
        schema = {
            "type": "object",
            "properties": {
                "sub": {"type": "object", "properties": {"x": {"type": "string"}}}
            },
        }
        out = relax_freeform_object_schema(schema)
        assert out["properties"]["sub"]["type"] == "object"

    def test_deep_copy_does_not_mutate_input(self):
        schema = {"type": "object", "properties": {"a": {"type": "object"}}}
        _ = relax_freeform_object_schema(schema)
        assert schema["properties"]["a"]["type"] == "object"


# ---------------------------------------------------------------------------
# ValidatingLLMClient configuration surface
# ---------------------------------------------------------------------------


class TestValidatingLLMClientConfig:
    def test_defaults(self):
        c = _FakeValidating(client=object())
        assert c.free_form_object_as_str is False
        assert c.prompt_based_validation is False
        assert c.default_generation_kwargs == {}

    def test_init_kwargs(self):
        c = _FakeValidating(
            free_form_object_as_str=True,
            prompt_based_validation=True,
            default_generation_kwargs={"max_tokens": 42},
            client=object(),
        )
        assert c.free_form_object_as_str is True
        assert c.prompt_based_validation is True
        assert c.default_generation_kwargs == {"max_tokens": 42}

    def test_configure_validation_is_chainable(self):
        c = _FakeValidating(client=object())
        out = c.configure_validation(free_form_object_as_str=True)
        assert out is c
        assert c.free_form_object_as_str is True

    def test_default_generation_kwargs_is_copied(self):
        kw = {"max_tokens": 10}
        c = _FakeValidating(default_generation_kwargs=kw, client=object())
        c.default_generation_kwargs["temperature"] = 0.0
        assert "temperature" not in kw, "caller's dict must not be mutated"


# ---------------------------------------------------------------------------
# _validate honors free_form_object_as_str
# ---------------------------------------------------------------------------


class TestValidatorRelaxation:
    _schema = {"type": "object", "properties": {"a": {"type": "object"}}}

    def test_strict_rejects_json_string_for_object_field(self):
        c = _FakeValidating(client=object())  # default: strict
        with pytest.raises(OutputValidationError):
            c._validate('{"a": "{\\"k\\": 1}"}', self._schema)

    def test_relaxed_accepts_json_string_for_object_field(self):
        c = _FakeValidating(free_form_object_as_str=True, client=object())
        # The LLM returned {"a": "<string representation of object>"} — still
        # valid with relaxed schema.
        got = c._validate('{"a": "arbitrary JSON-ish"}', self._schema)
        assert got == {"a": "arbitrary JSON-ish"}

    def test_relaxed_still_accepts_normal_object(self):
        c = _FakeValidating(free_form_object_as_str=True, client=object())
        assert c._validate('{"a": {"k": 1}}', self._schema) == {"a": {"k": 1}}


# ---------------------------------------------------------------------------
# generate() — prompt_based_validation + default_generation_kwargs
# ---------------------------------------------------------------------------


class TestPromptBasedValidation:
    def test_prompt_based_injects_schema_into_system_prompt(self, monkeypatch):
        observed: list = []
        _install_scripted_generate(monkeypatch, observed, ['{"a": "ok"}'])
        c = _FakeValidating(prompt_based_validation=True, client=object())
        out = c.generate(
            [{"role": "user", "content": "hi"}],
            schema={"type": "object", "properties": {"a": {"type": "string"}}},
        )
        assert out == {"a": "ok"}
        observed_prompt = observed[-1]["prompt"]
        assert observed_prompt[0]["role"] == "system"
        assert "JSON Schema" in observed_prompt[0]["content"]
        assert "response_format" not in observed[-1]


class TestDefaultGenerationKwargs:
    def test_defaults_applied_when_caller_does_not_set(self, monkeypatch):
        observed: list = []
        _install_scripted_generate(monkeypatch, observed, ['{"a": "ok"}'])
        c = _FakeValidating(
            prompt_based_validation=True,
            default_generation_kwargs={"max_tokens": 123, "temperature": 0.0},
            client=object(),
        )
        c.generate(
            [], schema={"type": "object", "properties": {"a": {"type": "string"}}}
        )
        obs = observed[-1]
        assert obs["max_tokens"] == 123
        assert obs["temperature"] == 0.0

    def test_caller_kwargs_win_over_defaults(self, monkeypatch):
        observed: list = []
        _install_scripted_generate(monkeypatch, observed, ['{"a": "ok"}'])
        c = _FakeValidating(
            prompt_based_validation=True,
            default_generation_kwargs={"max_tokens": 123},
            client=object(),
        )
        c.generate(
            [],
            schema={"type": "object", "properties": {"a": {"type": "string"}}},
            max_tokens=999,
        )
        assert observed[-1]["max_tokens"] == 999


# ---------------------------------------------------------------------------
# Wrapped _parse_llm_response: empty + reasoning-budget exhaustion
# ---------------------------------------------------------------------------


class TestSafeParse:
    def test_value_error_becomes_empty_string(self):
        c = _FakeValidating(client=object())
        # Wrapped parser returns "" (retry-worthy) on ValueError/KeyError
        # instead of propagating.
        assert c._parse_llm_response(ValueError("broken")) == ""

    def test_key_error_becomes_empty_string(self):
        c = _FakeValidating(client=object())
        assert c._parse_llm_response(KeyError("missing")) == ""

    def test_reasoning_budget_warning_logged(self, caplog):
        c = _FakeValidating(client=object())
        # A litellm-shaped response: reasoning_content set, finish_reason=length,
        # content missing — the classic reasoning-budget exhaustion pattern.
        raw = {
            "choices": [
                {
                    "message": {"reasoning_content": "long thinking..."},
                    "finish_reason": "length",
                }
            ]
        }

        # Wrap raw in a class whose attribute-access fails, forcing ValueError.
        class _FailingParse:
            def __init__(self, payload):
                self._p = payload

            # Intentionally broken access pattern in the *orig* parser.
            def __str__(self):
                return "ok"

        # Force the orig parser to raise ValueError, then check the safe
        # parser emits the targeted warning.
        class _C2(_FakeValidating):
            def _parse_llm_response(self, raw):  # will be wrapped
                raise ValueError("empty")

        with caplog.at_level(logging.WARNING, logger="altk.core.llm.output_parser"):
            c2 = _C2(client=object())
            out = c2._parse_llm_response(raw)
        assert out == ""
        assert any("reasoning" in r.message.lower() for r in caplog.records)
