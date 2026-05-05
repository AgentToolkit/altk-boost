"""Smoke tests for the shipped metric ``task_description`` strings.

Goals:
 - The runtime JSON files parse and include every configured metric.
 - The prompts can be instantiated via the public loader without errors.
 - The production-ready rules we baked into the prompts are present
   (evidence hierarchy, mid-trajectory awareness, redundancy-by-args,
   recovery after failure, confirmation scope, optional-parameter rule).

This keeps us honest if someone regenerates the JSONs and accidentally
drops the guardrails.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

import pytest

from altk.pre_tool.core.consts import (
    METRIC_AGENTIC_CONSTRAINTS_SATISFACTION,
    METRIC_FUNCTION_SELECTION_APPROPRIATENESS,
    METRIC_GENERAL_CONVERSATION_GROUNDED_CORRECTNESS,
    METRIC_GENERAL_HALLUCINATION_CHECK,
    METRIC_GENERAL_VALUE_FORMAT_ALIGNMENT,
)
from altk.pre_tool.sparc.function_calling.metrics.loader import (
    PromptKind,
    load_prompts_from_list,
)

ROOT = (
    Path(__file__).resolve().parents[3] / "altk/pre_tool/sparc/function_calling/metrics"
)
GENERAL_JSON = ROOT / "function_call/general_metrics_runtime.json"
FUNCSEL_JSON = ROOT / "function_selection/function_selection_metrics_runtime.json"
PARAM_JSON = ROOT / "parameter/parameter_metrics_runtime.json"


def _load(path: Path) -> List[Dict]:
    with path.open() as f:
        return json.load(f)


def _by_name(metrics: Iterable[Dict]) -> Dict[str, Dict]:
    return {m["name"]: m for m in metrics}


@pytest.fixture(scope="module")
def general_metrics() -> Dict[str, Dict]:
    return _by_name(_load(GENERAL_JSON))


@pytest.fixture(scope="module")
def funcsel_metrics() -> Dict[str, Dict]:
    return _by_name(_load(FUNCSEL_JSON))


# ---------------------------------------------------------------------------
# Structural checks — the JSONs still contain every canonical metric and
# the loader accepts them.
# ---------------------------------------------------------------------------


class TestRuntimeJsonStructure:
    def test_general_json_has_expected_metrics(self, general_metrics):
        assert set(general_metrics) >= {
            METRIC_GENERAL_HALLUCINATION_CHECK,
            METRIC_GENERAL_VALUE_FORMAT_ALIGNMENT,
            METRIC_GENERAL_CONVERSATION_GROUNDED_CORRECTNESS,
        }

    def test_funcsel_json_has_expected_metrics(self, funcsel_metrics):
        assert set(funcsel_metrics) >= {
            METRIC_FUNCTION_SELECTION_APPROPRIATENESS,
            METRIC_AGENTIC_CONSTRAINTS_SATISFACTION,
        }

    def test_every_metric_has_the_score_field(self, general_metrics, funcsel_metrics):
        # All metrics use the integer 1-5 rubric stored at properties.output.
        for m in (*general_metrics.values(), *funcsel_metrics.values()):
            props = m["jsonschema"]["properties"]
            assert "output" in props, f"metric {m['name']} missing output"
            assert props["output"]["type"] == "integer"
            assert props["output"]["minimum"] == 1
            assert props["output"]["maximum"] == 5

    def test_loader_accepts_every_general_metric(self):
        # Loader must instantiate prompt objects without raising; if the JSON
        # becomes malformed this will fail loudly.
        prompts = load_prompts_from_list(_load(GENERAL_JSON), PromptKind.GENERAL)
        assert len(prompts) == len(_load(GENERAL_JSON))

    def test_loader_accepts_every_funcsel_metric(self):
        prompts = load_prompts_from_list(
            _load(FUNCSEL_JSON), PromptKind.FUNCTION_SELECTION
        )
        assert len(prompts) == len(_load(FUNCSEL_JSON))


# ---------------------------------------------------------------------------
# Guardrails — key production-ready rules must remain in the task descriptions.
#
# We check each rule by looking for a small, stable anchor phrase. If a prompt
# is reorganized, these strings are the contract that must be preserved in
# spirit — update the anchor here AND the prompt together.
# ---------------------------------------------------------------------------


MID_TRAJ_ANCHORS = ("trajectory",)  # "one step in an ongoing trajectory" etc.

REDUNDANCY_ANCHORS = (
    "SAME function name AND",  # "SAME function name AND SAME arguments" — anywhere
    "same arguments",
)

RECOVERY_ANCHORS = (
    "fallback",  # "fallback strategies" in recovery-after-failure text
    "returned empty",
)

CONFIRMATION_ANCHORS = (
    # Confirmation scope is now phrased conceptually: "change persistent
    # state" covers the old MUTATING list; "information-gathering"
    # covers the old read-only prefix list.
    "persistent state",
    "information-gathering",
)

OPTIONAL_PARAM_ANCHORS = (
    "optional",  # spec-optional handling for hallucination
    "required",
)

EVIDENCE_ANCHORS = ("evidence",)  # either "evidence-based" or "explicit evidence"


def _contains_all(text: str, anchors: Iterable[str]) -> bool:
    # Normalize any line wrapping/indentation so anchors that span multiple
    # words are still detectable.
    flat = " ".join(text.split()).lower()
    return all(a.lower() in flat for a in anchors)


class TestProductionRulesInCommonBlock:
    """Shared guardrails now live in ``common_principles.COMMON_PRINCIPLES``
    and are injected into every function-calling metric system prompt via
    ``{{ common_principles }}`` (see FunctionMetricsPrompt). Each prompt's
    effective system message = common_principles + per-metric task_description,
    so the anchors must be present in at least one of those two sources."""

    @pytest.fixture(scope="class")
    def common(self):
        from altk.pre_tool.sparc.function_calling.metrics.common_principles import (
            COMMON_PRINCIPLES,
        )

        return COMMON_PRINCIPLES

    def _effective_prompt(self, common: str, td: str) -> str:
        return common + "\n\n" + td

    def test_general_hallucination_rules(self, common, general_metrics):
        td = general_metrics[METRIC_GENERAL_HALLUCINATION_CHECK]["task_description"]
        eff = self._effective_prompt(common, td)
        assert _contains_all(eff, EVIDENCE_ANCHORS)
        assert _contains_all(eff, OPTIONAL_PARAM_ANCHORS)
        assert _contains_all(eff, MID_TRAJ_ANCHORS)
        assert _contains_all(eff, RECOVERY_ANCHORS)

    def test_general_value_format_has_optional_carveout(self, common, general_metrics):
        td = general_metrics[METRIC_GENERAL_VALUE_FORMAT_ALIGNMENT]["task_description"]
        eff = self._effective_prompt(common, td)
        assert "optional" in eff.lower()
        assert "omitted" in eff.lower()

    def test_general_conversation_rules(self, common, general_metrics):
        td = general_metrics[METRIC_GENERAL_CONVERSATION_GROUNDED_CORRECTNESS][
            "task_description"
        ]
        eff = self._effective_prompt(common, td)
        assert _contains_all(eff, MID_TRAJ_ANCHORS)
        assert _contains_all(eff, REDUNDANCY_ANCHORS)
        assert _contains_all(eff, RECOVERY_ANCHORS)
        assert _contains_all(eff, CONFIRMATION_ANCHORS)

    def test_function_selection_rules(self, common, funcsel_metrics):
        td = funcsel_metrics[METRIC_FUNCTION_SELECTION_APPROPRIATENESS][
            "task_description"
        ]
        eff = self._effective_prompt(common, td)
        assert _contains_all(eff, MID_TRAJ_ANCHORS)
        assert _contains_all(eff, REDUNDANCY_ANCHORS)
        assert _contains_all(eff, RECOVERY_ANCHORS)

    def test_agentic_constraints_rules(self, common, funcsel_metrics):
        td = funcsel_metrics[METRIC_AGENTIC_CONSTRAINTS_SATISFACTION][
            "task_description"
        ]
        eff = self._effective_prompt(common, td)
        assert _contains_all(eff, MID_TRAJ_ANCHORS)
        assert _contains_all(eff, REDUNDANCY_ANCHORS)
        assert _contains_all(eff, CONFIRMATION_ANCHORS)


class TestCommonPrinciplesBlock:
    """Independent of which metric reads them, the shared block must carry
    all the production rules identified in our trace analysis."""

    @pytest.fixture(scope="class")
    def common(self):
        from altk.pre_tool.sparc.function_calling.metrics.common_principles import (
            COMMON_PRINCIPLES,
        )

        return COMMON_PRINCIPLES

    def test_has_evidence_hierarchy(self, common):
        # Order must be: system > tool outputs > user > assistant
        low = common.lower()
        assert "system prompt" in low
        assert "tool output" in low
        assert "user message" in low
        assert "assistant message" in low

    def test_has_trajectory_awareness(self, common):
        assert "trajectory" in common.lower()

    def test_has_redundancy_by_args(self, common):
        # Text is line-wrapped; normalize whitespace before matching.
        flat = " ".join(common.split())
        assert "SAME function name" in flat
        assert "SAME arguments" in flat

    def test_has_recovery_after_failure(self, common):
        low = common.lower()
        assert "recovery" in low or "fallback" in low
        assert "returned empty" in low or "errors" in low

    def test_confirmation_scope_moved_out_of_common(self, common):
        # Confirmation scope now lives in the per-metric task_descriptions
        # of agentic_constraints_satisfaction and
        # general_conversation_grounded_correctness — it is not a
        # universally-applicable rule. Common block must NOT mention it.
        assert "persistent state" not in common
        assert "Confirmation Scope" not in common
        # Guardrail: the old domain-leaky prefix enumeration stays gone.
        for banned in ("get_*", "find_*", "search_*", "MUTATING"):
            assert banned not in common, (
                f"{banned!r} must not appear in common_principles"
            )

    def test_stringency_moved_out_of_common(self, common):
        # Stringency is metric-class-specific and now lives on each
        # metric's own task_description.
        assert "Stringency" not in common

    def test_has_read_only_exploration_pass(self, common):
        low = common.lower()
        assert "exploration" in low
        assert "approved" in low  # "should be APPROVED"

    def test_is_bounded(self, common):
        # Shared rules shouldn't balloon past a few thousand chars.
        assert len(common) < 3000


class TestPromptSizeIsBounded:
    """A weak invariant: task_descriptions shouldn't balloon without review."""

    MAX_CHARS = 8000

    def test_general(self, general_metrics):
        for name, m in general_metrics.items():
            assert len(m["task_description"]) < self.MAX_CHARS, (
                f"{name} task_description too long ({len(m['task_description'])} chars)"
            )

    def test_funcsel(self, funcsel_metrics):
        for name, m in funcsel_metrics.items():
            assert len(m["task_description"]) < self.MAX_CHARS, (
                f"{name} task_description too long ({len(m['task_description'])} chars)"
            )
