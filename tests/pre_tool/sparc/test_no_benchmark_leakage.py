"""Guardrail: SPARC prompts must not leak benchmark-specific names.

The SPARC metrics ship with CLEAR, τ-bench retail/airline, and AppWorld
as the closest examples of upstream use cases — but the prompts are
consumed by arbitrary tool-calling agents (Claude Code, production
assistants, user-defined agents). Any benchmark-specific token that
slipped into a shared prompt would bias future judgments toward those
use cases.

This test checks that all prompt sources that are ALWAYS loaded into a
judge's context are free of a blocklist of benchmark-specific terms.
Few-shot examples inside user prompts (and the ``examples`` arrays of
metric JSONs, which are concrete demonstrations) are intentionally
excluded — concrete grounding examples are load-bearing in few-shot
learning and do NOT bias the judge in the same way as a rule.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3] / "altk/pre_tool/sparc/function_calling"
RUNTIME_GENERAL = ROOT / "metrics/function_call/general_metrics_runtime.json"
RUNTIME_FUNCSEL = ROOT / "metrics/function_selection/function_selection_metrics_runtime.json"
RUNTIME_PARAM = ROOT / "metrics/parameter/parameter_metrics_runtime.json"
EVAL_GENERAL = ROOT / "metrics/function_call/general_metrics.json"
EVAL_FUNCSEL = ROOT / "metrics/function_selection/function_selection_metrics.json"
EVAL_PARAM = ROOT / "metrics/parameter/parameter_metrics.json"
COMMON = ROOT / "metrics/common_principles.py"
TRANSFORM = ROOT / "pipeline/transformation_prompts.py"


# Terms that must not appear in ALWAYS-loaded prompt text (task descriptions,
# output-rubric descriptions, common principles, transformation system prompt).
# Names we know are specific to the public benchmarks we've tested against.
BENCHMARK_TERMS = (
    "tau-bench",
    "τ-bench",
    "taubench",
    "appworld",
    "tau2_retail",
    "tau2_airline",
    # Function-name / resource-name shapes unique to τ-bench domains:
    "reservation_id",
    "book_flight",
    # The "May 20" / "2024" partial-date anchor that previously leaked in
    # from the transformation prompt:
    "may 20",
    "2024-05-20",
    # A named demo restaurant that appeared in a CLEAR test fixture:
    "the french bistro",
)

# Function-name prefix enumerations that biased the confirmation-scope rule
# toward τ-bench tool naming. Conceptual phrasing ("persistent state",
# "information-gathering") is preferred.
PREFIX_ENUMERATIONS = ("get_*", "find_*", "search_*", "list_*", "show_*")


def _task_descriptions(path: Path) -> list[str]:
    """Return the task_description + output rubric description of every
    metric in a runtime JSON — i.e. the strings the judge sees every
    request. Examples / few-shots are intentionally excluded."""
    data = json.loads(path.read_text())
    out: list[str] = []
    for metric in data:
        td = metric.get("task_description", "")
        out.append(td)
        props = metric.get("jsonschema", {}).get("properties", {})
        out.append(props.get("output", {}).get("description", "") or "")
    return out


def _system_prompt_constants_from_transformation() -> str:
    """Pull just the system-prompt constants from transformation_prompts.

    The module also exposes ``*_USER`` constants that contain few-shot
    examples — concrete demonstrations are expected to be specific and
    are exempt from the domain-leak blocklist.
    """
    from altk.pre_tool.sparc.function_calling.pipeline import transformation_prompts as tp

    parts = []
    for name in ("MULTI_EXTRACT_UNITS_SYSTEM", "GENERATE_CODE_SYSTEM"):
        val = getattr(tp, name, None)
        if isinstance(val, str):
            parts.append(val)
    return "\n\n".join(parts)


def _common_principles_text() -> str:
    from altk.pre_tool.sparc.function_calling.metrics.common_principles import (
        COMMON_PRINCIPLES,
    )

    return COMMON_PRINCIPLES


@pytest.fixture(scope="module")
def shared_corpus() -> list[tuple[str, str]]:
    """(label, text) pairs of every ALWAYS-loaded prompt surface.

    Explicitly excluded: few-shot example constants (``*_USER``), the
    ``examples`` array inside metric JSONs. Concrete demonstrations in
    those locations are expected to be specific and do NOT bias the
    judge the way a general rule would.
    """
    blobs: list[tuple[str, str]] = []
    for path in (
        RUNTIME_GENERAL,
        RUNTIME_FUNCSEL,
        RUNTIME_PARAM,
        EVAL_GENERAL,
        EVAL_FUNCSEL,
        EVAL_PARAM,
    ):
        for i, td in enumerate(_task_descriptions(path)):
            blobs.append((f"{path.name}[{i}]", td))
    blobs.append(("common_principles.COMMON_PRINCIPLES", _common_principles_text()))
    blobs.append(
        ("transformation_prompts.*_SYSTEM", _system_prompt_constants_from_transformation())
    )
    return blobs


@pytest.mark.parametrize("term", BENCHMARK_TERMS)
def test_no_benchmark_term_in_shared_prompts(shared_corpus, term):
    lowered_corpus = [(label, text.lower()) for label, text in shared_corpus]
    offenders = [label for label, text in lowered_corpus if term in text]
    assert not offenders, (
        f"benchmark-specific term {term!r} leaked into shared prompt text: "
        f"{offenders}"
    )


@pytest.mark.parametrize("prefix", PREFIX_ENUMERATIONS)
def test_no_prefix_enumeration_in_shared_rules(shared_corpus, prefix):
    # Function-name prefix enumerations biased the confirmation-scope
    # rule. They must not appear in runtime task_descriptions or in the
    # common_principles / transformation_prompts modules (always loaded).
    # Few-shot examples are excluded from `shared_corpus` by design.
    offenders = [label for label, text in shared_corpus if prefix in text]
    assert not offenders, (
        f"function-name prefix enumeration {prefix!r} must not appear in "
        f"shared prompt rules: {offenders}"
    )


def test_mutating_as_rule_keyword_is_gone(shared_corpus):
    # The literal uppercase "MUTATING" used to be the anchor for the
    # confirmation-scope rule. It made the text feel benchmark-specific
    # and lowercased "mutating" as a descriptive adjective is fine.
    # Assert the shouty form is gone from rules.
    pattern = re.compile(r"\bMUTATING\b")
    offenders = [label for label, text in shared_corpus if pattern.search(text)]
    assert not offenders, (
        f"uppercase 'MUTATING' must not appear in shared prompt rules: {offenders}"
    )
