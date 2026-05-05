"""Schema + hygiene tests for the evaluation-time metric JSONs.

Runtime metrics are faster and omit recommendations. Evaluation-time
metrics include ``actionable_recommendations`` in the LLM output schema
and every example demonstrates the expected shape. This test locks the
schema in place so a future regen can't silently drift.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3] / "altk/pre_tool/sparc/function_calling/metrics"

EVAL_GENERAL = ROOT / "function_call/general_metrics.json"
EVAL_FUNCSEL = ROOT / "function_selection/function_selection_metrics.json"
EVAL_PARAM = ROOT / "parameter/parameter_metrics.json"

RUNTIME_GENERAL = ROOT / "function_call/general_metrics_runtime.json"
RUNTIME_FUNCSEL = ROOT / "function_selection/function_selection_metrics_runtime.json"
RUNTIME_PARAM = ROOT / "parameter/parameter_metrics_runtime.json"


ALL_EVAL = [EVAL_GENERAL, EVAL_FUNCSEL, EVAL_PARAM]
ALL_RUNTIME = [RUNTIME_GENERAL, RUNTIME_FUNCSEL, RUNTIME_PARAM]


ALLOWED_TARGETS = {
    "system_prompt",
    "tool_description",
    "parameter_description",
    "parameter_examples",
}

REQUIRED_ITEM_KEYS = ("target", "diff", "rationale", "importance")


@pytest.fixture(scope="module", params=ALL_EVAL, ids=[p.name for p in ALL_EVAL])
def eval_metrics(request):
    return json.loads(request.param.read_text()), request.param


@pytest.fixture(scope="module", params=ALL_RUNTIME, ids=[p.name for p in ALL_RUNTIME])
def runtime_metrics(request):
    return json.loads(request.param.read_text()), request.param


class TestEvalSchema:
    def test_actionable_recommendations_is_required(self, eval_metrics):
        data, path = eval_metrics
        for m in data:
            req = m["jsonschema"].get("required", [])
            assert "actionable_recommendations" in req, (
                f"{path.name}::{m['name']} missing actionable_recommendations "
                f"from required"
            )

    def test_schema_is_unified_diff_shape(self, eval_metrics):
        data, path = eval_metrics
        for m in data:
            ar = m["jsonschema"]["properties"]["actionable_recommendations"]
            assert ar["type"] == "array"
            item = ar["items"]
            assert item["type"] == "object"
            # Required fields
            assert set(item.get("required", [])) >= set(REQUIRED_ITEM_KEYS), (
                f"{path.name}::{m['name']} missing required keys in rec item"
            )
            props = item["properties"]
            # Target must be the closed enum
            assert set(props["target"]["enum"]) == ALLOWED_TARGETS, (
                f"{path.name}::{m['name']} target enum must be exactly {ALLOWED_TARGETS}"
            )
            # Importance must be [0, 1]
            assert props["importance"]["minimum"] == 0
            assert props["importance"]["maximum"] == 1
            # No legacy fields (quote / recommendation enum / details) remain
            for legacy in ("quote", "recommendation", "details"):
                assert legacy not in props, (
                    f"{path.name}::{m['name']} legacy field {legacy!r} still in schema"
                )

    def test_no_legacy_recommendation_enum_in_schema(self, eval_metrics):
        data, path = eval_metrics
        for m in data:
            blob = json.dumps(m["jsonschema"])
            # The old schema embedded enums with the uppercase tokens below.
            for legacy_enum in (
                "SYSTEM_PROMPT_INSTRUCTION",
                "TOOL_DOCUMENTATION",
                "TOOL_USAGE_EXAMPLES",
                "PARAMETER_DOCUMENTATION",
                "PARAMETER_EXAMPLES",
                "PARAMETER_FORMAT_DOCUMENTATION",
                "INSTRUCTIONS_ADDITIONS",
                "SYSTEM_PROMPT_ADDITIONS",
                "PREREQUISITE_TRACKING",
                "TOOL_DEPENDENCY_DOCUMENTATION",
            ):
                assert legacy_enum not in blob, (
                    f"{path.name}::{m['name']} still references legacy rec enum {legacy_enum!r}"
                )


class TestEvalExamples:
    def test_every_example_has_a_rec_list(self, eval_metrics):
        data, path = eval_metrics
        for m in data:
            for i, ex in enumerate(m.get("examples", [])):
                recs = ex["output"].get("actionable_recommendations")
                assert isinstance(recs, list), (
                    f"{path.name}::{m['name']} example[{i}] must have an "
                    f"actionable_recommendations list (possibly empty)"
                )

    def test_every_rec_has_required_fields(self, eval_metrics):
        data, path = eval_metrics
        for m in data:
            for i, ex in enumerate(m.get("examples", [])):
                for j, rec in enumerate(
                    ex["output"].get("actionable_recommendations", [])
                ):
                    for key in REQUIRED_ITEM_KEYS:
                        assert key in rec, (
                            f"{path.name}::{m['name']} ex[{i}].rec[{j}] "
                            f"missing required key {key!r}"
                        )

    def test_importance_in_unit_interval(self, eval_metrics):
        data, path = eval_metrics
        for m in data:
            for i, ex in enumerate(m.get("examples", [])):
                for j, rec in enumerate(
                    ex["output"].get("actionable_recommendations", [])
                ):
                    assert 0.0 <= float(rec["importance"]) <= 1.0, (
                        f"{path.name}::{m['name']} ex[{i}].rec[{j}] "
                        f"importance out of range"
                    )

    def test_target_is_in_allowed_enum(self, eval_metrics):
        data, path = eval_metrics
        for m in data:
            for i, ex in enumerate(m.get("examples", [])):
                for j, rec in enumerate(
                    ex["output"].get("actionable_recommendations", [])
                ):
                    assert rec["target"] in ALLOWED_TARGETS, (
                        f"{path.name}::{m['name']} ex[{i}].rec[{j}] target "
                        f"{rec['target']!r} not in {ALLOWED_TARGETS}"
                    )

    def test_tool_scoped_target_has_tool_name(self, eval_metrics):
        data, path = eval_metrics
        for m in data:
            for i, ex in enumerate(m.get("examples", [])):
                for j, rec in enumerate(
                    ex["output"].get("actionable_recommendations", [])
                ):
                    if rec["target"] in (
                        "tool_description",
                        "parameter_description",
                        "parameter_examples",
                    ):
                        assert rec.get("tool_name"), (
                            f"{path.name}::{m['name']} ex[{i}].rec[{j}] "
                            f"target={rec['target']} requires a tool_name"
                        )

    def test_parameter_scoped_target_has_parameter_name(self, eval_metrics):
        data, path = eval_metrics
        for m in data:
            for i, ex in enumerate(m.get("examples", [])):
                for j, rec in enumerate(
                    ex["output"].get("actionable_recommendations", [])
                ):
                    if rec["target"] in (
                        "parameter_description",
                        "parameter_examples",
                    ):
                        assert rec.get("parameter_name"), (
                            f"{path.name}::{m['name']} ex[{i}].rec[{j}] "
                            f"target={rec['target']} requires a parameter_name"
                        )

    def test_diff_is_unified_format(self, eval_metrics):
        data, path = eval_metrics
        # Unified-diff header pattern: ``--- a/<x>\n+++ b/<x>\n@@`` anywhere.
        header_re = re.compile(r"^--- a/.+\n\+\+\+ b/.+\n@@", re.MULTILINE)
        for m in data:
            for i, ex in enumerate(m.get("examples", [])):
                for j, rec in enumerate(
                    ex["output"].get("actionable_recommendations", [])
                ):
                    assert header_re.search(rec["diff"]), (
                        f"{path.name}::{m['name']} ex[{i}].rec[{j}] diff is "
                        f"not unified-diff format:\n{rec['diff']!r}"
                    )


class TestRuntimeDoesNotRequireRecs:
    def test_runtime_does_not_require_actionable_recommendations(self, runtime_metrics):
        data, path = runtime_metrics
        for m in data:
            req = m["jsonschema"].get("required", [])
            assert "actionable_recommendations" not in req, (
                f"{path.name}::{m['name']} must NOT require "
                f"actionable_recommendations in runtime mode"
            )
