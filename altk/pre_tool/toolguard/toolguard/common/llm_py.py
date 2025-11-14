import re

PYTHON_PATTERN = r"^```python\s*\n([\s\S]*)\n```"


def get_code_content(llm_code) -> str:
    code = llm_code.replace("\\n", "\n")
    match = re.match(PYTHON_PATTERN, code)
    if match:
        return match.group(1)

    return code
