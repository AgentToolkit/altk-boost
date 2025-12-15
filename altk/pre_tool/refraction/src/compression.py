from altk.pre_tool.refraction.src.main import refract
from altk.pre_tool.refraction.src.printer import CustomPrint
from altk.pre_tool.refraction.src.schemas.mappings import Mapping
from altk.pre_tool.refraction.src.schemas.results import (
    DebuggingResult,
)

try:
    from nestful import Catalog, SequencingData, SequenceStep
except ImportError as err:
    raise ImportError(
        'You need to install the refraction dependencies to use this component. Run `pip install "agent-lifecycle-toolkit[refraction]"`'
    ) from err

from typing import List, Dict, Optional, Any, Union

PRINTER = CustomPrint()


def compress(
    sequence: Union[
        SequenceStep,
        SequencingData,
        List[str],
        List[Dict[str, Any]],
        Dict[str, Any],
    ],
    catalog: Union[Catalog, List[Dict[str, Any]]],
    memory_objects: Optional[Dict[str, Any]] = None,
    memory_steps: SequencingData | List[str] | None = None,
    mappings: List[Mapping] | None = None,
    min_diff: bool = False,
    max_try: int = 3,
    timeout: Optional[float] = None,
) -> DebuggingResult:
    result: DebuggingResult = refract(
        sequence=sequence,
        catalog=catalog,
        memory_objects=memory_objects,
        memory_steps=memory_steps,
        mappings=mappings,
        min_diff=min_diff,
        compress=True,
        max_try=max_try,
        use_given_operators_only=True,
        timeout=timeout,
    )

    return result
