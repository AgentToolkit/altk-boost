from abc import ABC

from altk.pre_tool.sparc.function_calling.metrics.common_principles import (
    COMMON_PRINCIPLES,
)
from altk.pre_tool.sparc.metrics import Metric, MetricPrompt


class FunctionMetricsPrompt(MetricPrompt, ABC):
    """
    Abstract base for function-calling metric prompts.
    Subclasses must define class attrs:
      - system_template: str
      - user_template: str

    The ``{{ common_principles }}`` placeholder in ``system_template`` is
    filled from :mod:`.common_principles` so every function-call metric
    inherits the same production-quality guardrails (evidence hierarchy,
    trajectory awareness, redundancy-by-args, recovery-after-failure,
    confirmation-scope, read-only-exploration).
    """

    system_template: str
    user_template: str

    def __init__(self, metric: Metric, task_description: str) -> None:
        super().__init__(
            metric=metric,
            system_template=self.system_template,
            user_template=self.user_template,
            system_kwargs_defaults={
                "common_principles": COMMON_PRINCIPLES,
                "task_description": task_description,
                "metric_jsonschema": metric.to_jsonschema(),
            },
        )
