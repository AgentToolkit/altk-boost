from altk.pre_tool.toolguard.toolguard.common.str import to_snake_case
from altk.pre_tool.toolguard.toolguard.data_types import ToolPolicy, ToolPolicyItem


RUNTIME_PACKAGE_NAME = "rt_toolguard"
RUNTIME_INIT_PY = "__init__.py"
RUNTIME_TYPES_PY = "data_types.py"
RUNTIME_APP_TYPES_PY = "domain_types.py"

PY_ENV = "my_env"
PY_PACKAGES = ["pydantic", "pytest"]  # , "litellm"]


def guard_fn_name(tool_policy: ToolPolicy) -> str:
    return to_snake_case(f"guard_{tool_policy.tool_name}")


def guard_fn_module_name(tool_policy: ToolPolicy) -> str:
    return to_snake_case(f"guard_{tool_policy.tool_name}")


def guard_item_fn_name(tool_item: ToolPolicyItem) -> str:
    return to_snake_case(f"guard_{tool_item.name}")


def guard_item_fn_module_name(tool_item: ToolPolicyItem) -> str:
    return to_snake_case(f"guard_{tool_item.name}")


def test_fn_name(tool_item: ToolPolicyItem) -> str:
    return to_snake_case(f"test_guard_{tool_item.name}")


def test_fn_module_name(tool_item: ToolPolicyItem) -> str:
    return to_snake_case(f"test_guard_{tool_item.name}")
