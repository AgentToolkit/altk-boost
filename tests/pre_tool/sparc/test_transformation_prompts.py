"""Tests for the unit/format-extraction prompts.

The extractor applies a strict evidence hierarchy and prefers conservative
no-ops over spurious "needs transformation" verdicts. These tests verify
the prompt contains the conceptual anchors that encode those rules — not
domain-specific phrasing. Runtime behaviour is covered by the SPARC
pipeline integration tests (marked ``llm``).
"""

from altk.pre_tool.sparc.function_calling.pipeline import transformation_prompts as tp


def _flat(s: str) -> str:
    return " ".join(s.split()).lower()


class TestMultiExtractSystem:
    def test_mentions_evidence_hierarchy_sources(self):
        flat = _flat(tp.MULTI_EXTRACT_UNITS_SYSTEM)
        # The extractor must know about the evidence hierarchy's
        # higher-priority sources generically, without hard-coding any
        # specific anchor kind (date, year, region, …).
        assert "system prompt" in flat
        assert "tool output" in flat

    def test_has_evidence_priority_ordering(self):
        flat = _flat(tp.MULTI_EXTRACT_UNITS_SYSTEM)
        assert (
            "system prompt > tool outputs > user messages > assistant messages" in flat
        )

    def test_has_under_specified_grounding_rule(self):
        flat = _flat(tp.MULTI_EXTRACT_UNITS_SYSTEM)
        # The prompt must teach the extractor to COMPLETE an
        # under-specified value from a higher-priority anchor BEFORE
        # reporting it — without naming a specific example (year, date,
        # region, etc.) in the rule itself.
        assert "under-specified" in flat
        assert "higher-priority source" in flat or "higher priority source" in flat
        assert "before reporting" in flat

    def test_grounded_completion_is_not_a_transformation(self):
        flat = _flat(tp.MULTI_EXTRACT_UNITS_SYSTEM)
        # The rule should clarify that completing a partial value from
        # context is NOT a code-level transformation (keeps
        # transformation_summary empty).
        assert "transformation_summary" in flat
        assert "no code-level" in flat or "no code level" in flat

    def test_conservative_noop_rule(self):
        flat = _flat(tp.MULTI_EXTRACT_UNITS_SYSTEM)
        assert "conservative" in flat
        assert "no-op" in flat or "empty strings" in flat


class TestMultiExtractUser:
    def test_user_prompt_has_grounding_example(self):
        # The user prompt still demonstrates grounding via a concrete
        # few-shot — concrete examples in few-shots are expected and
        # load-bearing. What matters is that the demonstrated
        # transformation_summary is empty (contextual completion ≠ code
        # transformation).
        body = tp.MULTI_EXTRACT_UNITS_USER
        flat = " ".join(body.split())
        assert 'transformation_summary":""' in flat
