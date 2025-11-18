from enum import Enum
from typing import Any, Dict, List, Optional, Union


from altk.pre_tool.toolguard.toolguard.common.ref import DocumentWithRef, Reference


class StrEnum(str, Enum):
    """An abstract base class for string-based enums."""

    pass


class JSONSchemaTypes(StrEnum):
    string = "string"
    number = "number"
    integer = "integer"
    boolean = "boolean"
    array = "array"
    object = "object"
    null = "null"


class JSchema(DocumentWithRef):
    type: Optional[JSONSchemaTypes] = None
    properties: Optional[Dict[str, Union[Reference, "JSchema"]]] = None
    items: Optional[Union[Reference, "JSchema"]] = None
    additionalProperties: Optional[Union["JSchema", bool]] = None
    format: Optional[str] = None
    enum: Optional[list] = None
    default: Optional[Any] = None
    description: Optional[str] = None
    example: Optional[Any] = None
    required: Optional[List[str]] = None
    allOf: Optional[List[Union[Reference, "JSchema"]]] = None
    anyOf: Optional[List[Union[Reference, "JSchema"]]] = None
    nullable: Optional[bool] = (
        None  # in OPenAPISpec https://swagger.io/docs/specification/v3_0/data-models/data-types/#null
    )

    def __str__(self) -> str:
        return self.model_dump_json(exclude_none=True, indent=2)
