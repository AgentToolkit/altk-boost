try:
    from nl2flow.compile.schemas import MemoryItem
except ImportError as err:
    raise ImportError(
        'You need to install the refraction dependencies to use this component. Run `pip install "agent-lifecycle-toolkit[refraction]"`'
    ) from err

from typing import Dict, Any


class MemoryObject(MemoryItem):
    value: Dict[str, Any]
