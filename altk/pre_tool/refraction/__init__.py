try:
    from altk.pre_tool.refraction.refraction import RefractionComponent
    from altk.pre_tool.refraction.types import (
        RefractionRunInput,
        RefractionRunOutput,
        RefractionBuildInput,
    )

    __all__ = [
        "RefractionComponent",
        "RefractionRunInput",
        "RefractionRunOutput",
        "RefractionBuildInput",
    ]
except ImportError:
    # Refraction dependencies not installed
    __all__ = []
