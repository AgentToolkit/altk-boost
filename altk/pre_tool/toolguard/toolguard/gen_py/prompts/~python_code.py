from pydantic import BaseModel, Field
import re

PYTHON_PATTERN = r"^```python\s*\n([\s\S]*)\n```"


class PythonCodeModel(BaseModel):
    python_code: str = Field(
        ...,
    )

    def get_code_content(self) -> str:
        code = self.python_code.replace("\\n", "\n")
        match = re.match(PYTHON_PATTERN, code)
        if match:
            return match.group(1)

        return code

    @classmethod
    def create(cls, python_code: str) -> "PythonCodeModel":
        return PythonCodeModel.model_construct(
            python_code=f"```python\n{python_code}\n```"
        )
