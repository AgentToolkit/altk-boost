from typing import Optional


class Param:
    name: str
    type: str
    description: Optional[str] = ""
    example: Optional[str]
    required: bool
