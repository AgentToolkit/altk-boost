from typing import TypeVar
from pydantic import BaseModel, Field

from altk.pre_tool.toolguard.toolguard.common.dict import find_ref


class Reference(BaseModel):
    ref: str = Field(..., alias="$ref")


BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class DocumentWithRef(BaseModel):
    def resolve_ref(
        self, obj: Reference | BaseModelT | None, object_type: type[BaseModelT]
    ) -> BaseModelT | None:
        if isinstance(obj, Reference):
            tmp = find_ref(self.model_dump(), obj.ref)
            return object_type.model_validate(tmp)
        return obj
