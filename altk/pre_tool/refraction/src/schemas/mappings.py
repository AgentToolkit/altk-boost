from __future__ import annotations

try:
    from nl2flow.compile.schemas import MappingItem
except ImportError as err:
    raise ImportError(
        'You need to install the refraction dependencies to use this component. Run `pip install "agent-lifecycle-toolkit[refraction]"`'
    ) from err

from pydantic import BaseModel
from typing import Optional


class Mapping(MappingItem):
    pass


class MappingCandidate(BaseModel):
    name: str
    description: str
    type: Optional[str] = None
    source: str
    is_input: bool


class MappingLabel(BaseModel):
    label: str
    map: Optional[str] = None
