"""Tests for the compact tool-schema rendering mode on ``OpenAIAdapter``.

The compact mode is intended for function-selection prompts when the inventory
is so large that full {param_name: type} summaries would blow the context
window (e.g. appworld's 457 tools). Compact emits a list of parameter names
only — no types.

Covers:
 - ``"never"`` renders the legacy {name: type} summary regardless of size.
 - ``"always"`` renders the compact [name, ...] summary regardless of size.
 - ``"auto"`` (default) switches based on ``compact_tool_threshold``.
 - Single-tool paths (``get_tool_spec``, ``get_tools_inventory``) are
   unaffected.
 - Pipeline-/component-level config forwards the flags to the adapter.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from altk.pre_tool.core.config import SPARCReflectionConfig
from altk.pre_tool.sparc.function_calling.pipeline.adapters import OpenAIAdapter
from altk.pre_tool.sparc.function_calling.pipeline.types import ToolCall, ToolSpec


def _make_spec(name: str, params: List[str]) -> ToolSpec:
    return ToolSpec.model_validate(
        {
            "type": "function",
            "function": {
                "name": name,
                "description": f"desc of {name}",
                "parameters": {
                    "type": "object",
                    "properties": {p: {"type": "string", "description": p} for p in params},
                    "required": [],
                },
            },
        }
    )


def _call() -> ToolCall:
    return ToolCall.model_validate(
        {"id": "c", "type": "function", "function": {"name": "tool_0", "arguments": "{}"}}
    )


@pytest.fixture
def small_inventory() -> List[ToolSpec]:
    return [_make_spec(f"tool_{i}", ["a", "b", "c"]) for i in range(5)]


@pytest.fixture
def large_inventory() -> List[ToolSpec]:
    return [_make_spec(f"big_{i}", ["x", "y"]) for i in range(25)]


# ---------------------------------------------------------------------------
# summary rendering — compact_tool_schema modes
# ---------------------------------------------------------------------------


class TestCompactSchemaModes:
    def test_never_keeps_full_summary_regardless_of_size(self, small_inventory, large_inventory):
        for specs in (small_inventory, large_inventory):
            ad = OpenAIAdapter(specs, _call(), compact_tool_schema="never")
            summary = ad.get_tools_inventory_summary()
            assert len(summary) == len(specs)
            for entry in summary:
                assert isinstance(entry["tool_parameters"], dict), (
                    "never mode should emit {param_name: type} dicts"
                )

    def test_always_uses_compact_regardless_of_size(self, small_inventory, large_inventory):
        for specs in (small_inventory, large_inventory):
            ad = OpenAIAdapter(specs, _call(), compact_tool_schema="always")
            summary = ad.get_tools_inventory_summary()
            assert len(summary) == len(specs)
            for entry in summary:
                assert isinstance(entry["tool_parameters"], list), (
                    "always mode should emit a list of parameter names"
                )

    def test_auto_stays_full_under_threshold(self, small_inventory):
        # default threshold = 20; 5 tools should stay full
        ad = OpenAIAdapter(small_inventory, _call())
        summary = ad.get_tools_inventory_summary()
        assert isinstance(summary[0]["tool_parameters"], dict)

    def test_auto_switches_compact_at_or_above_threshold(self, large_inventory):
        # default threshold = 20; 25 tools should flip to compact
        ad = OpenAIAdapter(large_inventory, _call())
        summary = ad.get_tools_inventory_summary()
        assert isinstance(summary[0]["tool_parameters"], list)
        assert summary[0]["tool_parameters"] == ["x", "y"]

    def test_auto_threshold_override(self, small_inventory):
        # With threshold=3, even 5 tools triggers compact
        ad = OpenAIAdapter(small_inventory, _call(), compact_tool_threshold=3)
        summary = ad.get_tools_inventory_summary()
        assert isinstance(summary[0]["tool_parameters"], list)

    def test_auto_threshold_off_by_one(self, small_inventory):
        # exactly-at-threshold should flip to compact (>= not >)
        ad = OpenAIAdapter(small_inventory, _call(), compact_tool_threshold=5)
        assert ad._use_compact_summary() is True
        ad = OpenAIAdapter(small_inventory, _call(), compact_tool_threshold=6)
        assert ad._use_compact_summary() is False


# ---------------------------------------------------------------------------
# single-tool surfaces — must NOT be affected by compact mode
# ---------------------------------------------------------------------------


class TestSingleToolSurfacesUnchanged:
    def test_get_tool_spec_is_full_dump_in_all_modes(self, large_inventory):
        for mode in ("auto", "always", "never"):
            ad = OpenAIAdapter(large_inventory, _call(), compact_tool_schema=mode)
            spec = ad.get_tool_spec("big_0")
            # full single-tool dump keeps the schema
            assert "parameters" in spec
            assert "properties" in spec["parameters"]
            assert spec["parameters"]["properties"]["x"]["type"] == "string"

    def test_get_tools_inventory_is_full_in_all_modes(self, large_inventory):
        for mode in ("auto", "always", "never"):
            ad = OpenAIAdapter(large_inventory, _call(), compact_tool_schema=mode)
            full = ad.get_tools_inventory()
            # each entry is a ToolSpec model_dump, which includes the full
            # function schema under .function.parameters
            assert len(full) == len(large_inventory)
            for entry in full:
                assert "function" in entry
                assert "parameters" in entry["function"]


# ---------------------------------------------------------------------------
# config propagation
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    def test_defaults(self):
        cfg = SPARCReflectionConfig()
        assert cfg.compact_tool_schema == "auto"
        assert cfg.compact_tool_threshold == 20

    def test_config_override(self):
        cfg = SPARCReflectionConfig(compact_tool_schema="always", compact_tool_threshold=5)
        assert cfg.compact_tool_schema == "always"
        assert cfg.compact_tool_threshold == 5

    def test_invalid_mode_rejected(self):
        with pytest.raises(Exception):  # pydantic will raise ValidationError
            SPARCReflectionConfig(compact_tool_schema="garbage")

    def test_invalid_threshold_rejected(self):
        with pytest.raises(Exception):  # ge=1 constraint
            SPARCReflectionConfig(compact_tool_threshold=0)


class TestPipelineForwarding:
    """Confirm compact_tool_schema flows Pipeline -> SemanticChecker -> Adapter."""

    def test_semantic_checker_forwards_to_adapter(self, large_inventory):
        from altk.core.llm import ValidatingLLMClient
        from altk.pre_tool.sparc.function_calling.pipeline.semantic_checker import (
            SemanticChecker,
        )

        # minimal dummy ValidatingLLMClient — the checker only needs it
        # present to construct itself; we are not calling generate here.
        class _Dummy(ValidatingLLMClient):  # type: ignore[misc]
            @classmethod
            def provider_class(cls):
                return object

            def _register_methods(self) -> None:  # noqa: D401
                pass

            def _parse_llm_response(self, raw):  # noqa: D401
                return str(raw)

            def _setup_parameter_mapper(self) -> None:
                pass

        client = _Dummy(client=object())
        checker = SemanticChecker(
            metrics_client=client,
            compact_tool_schema="always",
            compact_tool_threshold=42,
        )
        adapter = checker._make_adapter(large_inventory, _call())
        assert adapter.compact_tool_schema == "always"
        assert adapter.compact_tool_threshold == 42

        # And an empty-specs path should still propagate the config
        adapter_empty = checker._make_adapter([], _call())
        assert adapter_empty.compact_tool_schema == "always"
        assert adapter_empty.compact_tool_threshold == 42
