import inspect
import re
from typing import Callable


def extract_docstr_args(func: Callable) -> str:
    doc = inspect.getdoc(func)
    if not doc:
        return ""

    lines = doc.splitlines()

    def args_start_line():
        for i, line in enumerate(lines):
            if line.strip().lower() == "args:":  # Google style docstr
                return i + 1
            if (
                line.strip().lower().startswith(":param ")
            ):  # Sphinx-style docstring. https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html
                return i

    args_start = args_start_line()
    if args_start is None:
        return ""

    # List of known docstring section headers
    next_sections = {
        "returns:",
        "raises:",
        "examples:",
        "notes:",
        "attributes:",
        "yields:",
    }

    # Capture lines after "Args:" that are indented
    args_lines = []
    indent = " " * 4 * 2
    for line in lines[args_start:]:
        # Stop if we hit a new section (like "Returns:", "Raises:", etc.)
        stripped = line.strip().lower()
        if stripped in next_sections or stripped.startswith(":return:"):
            break

        args_lines.append(indent + sphinx_param_to_google(line.strip()))

    # Join all lines into a single string
    if not args_lines:
        return ""

    return "\n".join(args_lines)


def sphinx_param_to_google(line: str) -> str:
    """
    Convert a single Sphinx-style ':param' line to Google style.

    Args:
        line: A Sphinx param line, e.g.
              ':param user_id: The unique identifier of the user.'

    Returns:
        str: Google style equivalent, e.g.
             'user_id: The unique identifier of the user.'
    """
    m = re.match(r"\s*:param\s+(\w+)\s*:\s*(.*)", line)
    if not m:
        return line
    name, desc = m.groups()
    return f"{name}: {desc}"
