from altk.build_time.test_case_generation_toolkit.src.toolops.toolspec.populate_toolspec_from_toolinfo import (
    populate_toolspec,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.toolspec.populate_tool_info import (
    parse_python_tool,
)
import logging

logger = logging.getLogger("toolops.toolspec.generate_toolspec")


def get_toolspec(python_tool_str):
    tool_info = parse_python_tool(python_tool_str)
    toolspec = populate_toolspec(tool_info)
    return tool_info.name, toolspec
