from typing import Optional, List
from altk.build_time.test_case_generation_toolkit.src.toolops.toolspec.tool_infos.Param import (
    Param,
)


class ToolInfo:
    name: str
    description: Optional[str] = ""
    queryParams: Optional[List[Param]] = None
    output_schema: dict
    security: List
    auth: Optional[str] = ""
