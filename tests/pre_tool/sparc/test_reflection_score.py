"""Tests for per-metric rubric score + aggregate score in SPARC output.

Covers:
- ``SPARCReflectionIssue.output_value`` / ``.confidence`` carry per-metric
  numeric context when available.
- ``SPARCReflectionResult.score`` aggregates across all semantic metrics
  that produced a rating (approved or not).
- ``.approved`` boolean and ``.normalized_score`` 0-1 helper.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from altk.pre_tool.core.types import (
    SPARCReflectionDecision,
    SPARCReflectionIssue,
    SPARCReflectionIssueType,
    SPARCReflectionResult,
)
from altk.pre_tool.sparc.sparc import SPARCReflectionComponent


def _metric(is_issue: bool, output: float | None, confidence: float = 0.9, error: str = ""):
    raw = {"output": output, "confidence": confidence, "explanation": "e", "correction": None}
    return SimpleNamespace(
        is_issue=is_issue, raw_response=raw, error=error
    )


class _PipelineResult(SimpleNamespace):
    pass


# ---------------------------------------------------------------------------
# Reflection result helpers
# ---------------------------------------------------------------------------


class TestResultHelpers:
    def test_approved_shortcut_true(self):
        r = SPARCReflectionResult(decision=SPARCReflectionDecision.APPROVE)
        assert r.approved is True

    def test_approved_shortcut_false(self):
        r = SPARCReflectionResult(decision=SPARCReflectionDecision.REJECT)
        assert r.approved is False

    def test_normalized_score_none_when_unset(self):
        r = SPARCReflectionResult(decision=SPARCReflectionDecision.APPROVE)
        assert r.normalized_score is None

    @pytest.mark.parametrize(
        "raw,expected",
        [
            (1.0, 0.0),
            (3.0, 0.5),
            (5.0, 1.0),
            (4.5, 0.875),
            (0.0, 0.0),  # clamped
            (6.0, 1.0),  # clamped
        ],
    )
    def test_normalized_score_mapping(self, raw, expected):
        r = SPARCReflectionResult(decision=SPARCReflectionDecision.APPROVE, score=raw)
        assert r.normalized_score == pytest.approx(expected)


# ---------------------------------------------------------------------------
# _rubric_score extraction
# ---------------------------------------------------------------------------


class TestRubricExtraction:
    def test_valid_output(self):
        m = _metric(is_issue=False, output=4.0)
        assert SPARCReflectionComponent._rubric_score(m) == 4.0
        assert SPARCReflectionComponent._rubric_confidence(m) == 0.9

    def test_missing_output(self):
        m = SimpleNamespace(raw_response={"confidence": 0.5})
        assert SPARCReflectionComponent._rubric_score(m) is None

    def test_non_numeric_output(self):
        m = SimpleNamespace(raw_response={"output": "not-a-number"})
        assert SPARCReflectionComponent._rubric_score(m) is None

    def test_no_raw_response(self):
        m = SimpleNamespace(error="oops")
        assert SPARCReflectionComponent._rubric_score(m) is None


# ---------------------------------------------------------------------------
# End-to-end aggregation via _process_pipeline_result
# ---------------------------------------------------------------------------


def _build_component():
    """Create a minimal SPARCReflectionComponent for direct _process_pipeline_result
    calls, bypassing LLM-client validation."""
    from altk.core.toolkit import ComponentConfig

    class _BareComponent(SPARCReflectionComponent):
        def __init__(self):  # noqa: D401
            # Skip __init__ chain — we only exercise _process_pipeline_result.
            pass

    return _BareComponent()


def _pipeline(general=None, function_selection=None, parameter=None, transform=None, static=None):
    """Build a PipelineResult-shaped SimpleNamespace."""
    return _PipelineResult(
        static=static,
        semantic=SimpleNamespace(
            general=SimpleNamespace(metrics=general or {}) if general is not None else None,
            function_selection=(
                SimpleNamespace(metrics=function_selection or {})
                if function_selection is not None
                else None
            ),
            parameter=parameter or {},
            transform=transform or {},
        ),
    )


class TestAggregateScore:
    def test_all_approved(self):
        comp = _build_component()
        pr = _pipeline(
            general={"g1": _metric(False, 5.0), "g2": _metric(False, 4.0)},
            function_selection={"f1": _metric(False, 5.0)},
        )
        result = comp._process_pipeline_result(pr)
        assert result.decision == SPARCReflectionDecision.APPROVE
        assert result.approved is True
        assert result.score == pytest.approx((5 + 4 + 5) / 3)
        assert result.issues == []

    def test_rejected_with_per_issue_score(self):
        comp = _build_component()
        bad = _metric(True, 2.0, confidence=0.8)
        good = _metric(False, 5.0)
        pr = _pipeline(
            general={"g1": bad, "g2": good},
            function_selection={"f1": good},
        )
        result = comp._process_pipeline_result(pr)
        assert result.decision == SPARCReflectionDecision.REJECT
        assert result.score == pytest.approx((2 + 5 + 5) / 3)
        # The issue must carry its per-metric rubric info
        assert len(result.issues) == 1
        assert result.issues[0].output_value == 2.0
        assert result.issues[0].confidence == pytest.approx(0.8)

    def test_score_none_when_no_semantic_metrics(self):
        comp = _build_component()
        pr = _pipeline()  # no semantic results
        result = comp._process_pipeline_result(pr)
        assert result.score is None

    def test_function_selection_issue_masks_general(self):
        """When function_selection has an issue, general/parameter metrics are
        skipped (existing SPARC behavior). Aggregate score should only include
        what was actually evaluated."""
        comp = _build_component()
        fs_bad = _metric(True, 1.0)
        # general metrics are present but should be skipped by the masking
        pr = _pipeline(
            general={"g1": _metric(False, 5.0)},
            function_selection={"f1": fs_bad},
        )
        result = comp._process_pipeline_result(pr)
        assert result.decision == SPARCReflectionDecision.REJECT
        # Only the function_selection metric's score contributed
        assert result.score == pytest.approx(1.0)
        assert result.issues[0].issue_type == SPARCReflectionIssueType.SEMANTIC_FUNCTION
        assert result.issues[0].output_value == 1.0

    def test_errored_metric_records_no_score(self):
        comp = _build_component()
        errored = SimpleNamespace(
            is_issue=False, error="llm timeout", raw_response=None
        )
        pr = _pipeline(general={"g1": errored})
        result = comp._process_pipeline_result(pr)
        assert result.decision == SPARCReflectionDecision.ERROR
        assert result.score is None


# ---------------------------------------------------------------------------
# Actionable-recommendation extraction (evaluation-time mode)
# ---------------------------------------------------------------------------


def _metric_with_recs(is_issue: bool, output: float, recs: list[dict], error: str = ""):
    raw = {
        "output": output,
        "confidence": 0.9,
        "explanation": "e",
        "correction": None,
        "actionable_recommendations": recs,
    }
    return SimpleNamespace(is_issue=is_issue, raw_response=raw, error=error)


class TestRecommendationExtraction:
    GOOD_REC = {
        "target": "system_prompt",
        "tool_name": None,
        "parameter_name": None,
        "diff": "--- a/system_prompt\n+++ b/system_prompt\n@@\n+Call search before book.",
        "rationale": "Prior turn skipped the search step.",
        "importance": 0.8,
    }
    PARAM_REC = {
        "target": "parameter_description",
        "tool_name": "book_resource",
        "parameter_name": "resource_id",
        "diff": "--- a/tool/book_resource#resource_id\n+++ b/tool/book_resource#resource_id\n@@\n+Must come from a prior lookup call.",
        "rationale": "Agent fabricated ids repeatedly.",
        "importance": 0.55,
    }

    def test_single_rec_on_issue(self):
        comp = _build_component()
        bad = _metric_with_recs(True, 2.0, [self.GOOD_REC])
        result = comp._process_pipeline_result(_pipeline(general={"g1": bad}))
        assert len(result.issues) == 1
        assert len(result.issues[0].recommendations) == 1
        rec = result.issues[0].recommendations[0]
        assert rec.target.value == "system_prompt"
        assert rec.importance == 0.8
        assert len(result.all_recommendations) == 1

    def test_rec_on_non_issue_still_collected(self):
        # A grade-5 (no issue) call can still surface spec improvements.
        comp = _build_component()
        ok = _metric_with_recs(False, 5.0, [self.PARAM_REC])
        result = comp._process_pipeline_result(_pipeline(general={"g1": ok}))
        assert result.issues == []
        # all_recommendations must still carry the rec.
        assert len(result.all_recommendations) == 1
        assert result.all_recommendations[0].tool_name == "book_resource"

    def test_multiple_metrics_aggregate_all_recs(self):
        comp = _build_component()
        bad = _metric_with_recs(True, 2.0, [self.GOOD_REC])
        ok = _metric_with_recs(False, 5.0, [self.PARAM_REC])
        result = comp._process_pipeline_result(
            _pipeline(general={"g1": bad, "g2": ok})
        )
        assert len(result.all_recommendations) == 2

    def test_malformed_rec_is_dropped(self):
        comp = _build_component()
        bad_rec = {**self.GOOD_REC, "target": "not_a_real_target"}
        empty_diff = {**self.GOOD_REC, "diff": ""}
        good = _metric_with_recs(True, 2.0, [bad_rec, empty_diff, self.GOOD_REC])
        result = comp._process_pipeline_result(_pipeline(general={"g1": good}))
        # Only the one valid rec survives.
        assert len(result.all_recommendations) == 1

    def test_importance_clamped_to_unit_interval(self):
        comp = _build_component()
        recs = [
            {**self.GOOD_REC, "importance": 1.5},
            {**self.GOOD_REC, "importance": -0.3},
            {**self.GOOD_REC, "importance": "not-numeric"},
        ]
        good = _metric_with_recs(True, 2.0, recs)
        result = comp._process_pipeline_result(_pipeline(general={"g1": good}))
        imps = [r.importance for r in result.all_recommendations]
        # 1.5 -> 1.0; -0.3 -> 0.0; "not-numeric" -> 0.5 (fallback).
        assert sorted(imps) == pytest.approx([0.0, 0.5, 1.0])

    def test_no_actionable_recommendations_field_is_safe(self):
        # Runtime mode: raw_response has no actionable_recommendations key.
        comp = _build_component()
        m = SimpleNamespace(
            is_issue=False,
            raw_response={"output": 5.0, "confidence": 0.9, "explanation": "e"},
            error="",
        )
        result = comp._process_pipeline_result(_pipeline(general={"g1": m}))
        assert result.all_recommendations == []
