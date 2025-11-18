from enum import Enum
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Optional, Any, TypeVar, Union
import json
import yaml

from altk.pre_tool.toolguard.toolguard.common.dict import find_ref
from altk.pre_tool.toolguard.toolguard.common.http import MEDIA_TYPE_APP_JSON
from altk.pre_tool.toolguard.toolguard.common.jschema import JSchema
from altk.pre_tool.toolguard.toolguard.common.ref import Reference


class Contact(BaseModel):
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    email: Optional[str] = None


class License(BaseModel):
    name: str
    identifier: Optional[str] = None
    url: Optional[HttpUrl] = None


class Info(BaseModel):
    title: str
    summary: Optional[str] = None
    description: Optional[str] = None
    termsOfService: Optional[HttpUrl] = None
    contact: Optional[Contact] = None
    license: Optional[License] = None
    version: str


class ServerVariable(BaseModel):
    enum: Optional[List[str]] = None
    default: str
    description: Optional[str] = None


class Server(BaseModel):
    url: str
    description: Optional[str] = None
    variables: Optional[Dict[str, ServerVariable]] = None


class ExternalDocumentation(BaseModel):
    description: Optional[str] = None
    url: HttpUrl


class Tag(BaseModel):
    name: str
    description: Optional[str] = None
    externalDocs: Optional[ExternalDocumentation] = None


class MediaType(BaseModel):
    schema_: Optional[Union[Reference, JSchema]] = Field(None, alias="schema")
    example: Optional[Any] = None
    examples: Optional[Dict[str, Any]] = None


class RequestBody(BaseModel):
    description: Optional[str] = None
    required: Optional[bool] = None
    content: Optional[Dict[str, MediaType]] = None

    @property
    def content_json(self):
        if self.content:
            return self.content.get(MEDIA_TYPE_APP_JSON)


class Response(BaseModel):
    description: Optional[str] = None
    content: Optional[Dict[str, MediaType]] = None

    @property
    def content_json(self):
        if self.content:
            return self.content.get(MEDIA_TYPE_APP_JSON)


class StrEnum(str, Enum):
    """An abstract base class for string-based enums."""

    pass


class ParameterIn(StrEnum):
    query = "query"
    header = "header"
    cookie = "cookie"
    path = "path"


class Parameter(BaseModel):
    name: str
    description: Optional[str] = None
    in_: ParameterIn = Field(ParameterIn.query, alias="in")
    required: Optional[bool] = None
    schema_: Optional[Union[Reference, JSchema]] = Field(None, alias="schema")


class Operation(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    operationId: Optional[str] = None
    tags: Optional[List[str]] = None
    parameters: Optional[List[Union[Reference, Parameter]]] = None
    requestBody: Optional[Union[Reference, RequestBody]] = None
    responses: Optional[Dict[str, Union[Reference, Response]]] = None
    security: Optional[Dict[str, List[str]]] = None


class PathItem(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    servers: Optional[List[Server]] = None
    parameters: Optional[List[Union[Reference, Parameter]]] = None
    get: Optional[Operation] = None
    put: Optional[Operation] = None
    post: Optional[Operation] = None
    delete: Optional[Operation] = None
    options: Optional[Operation] = None
    head: Optional[Operation] = None
    patch: Optional[Operation] = None
    trace: Optional[Operation] = None

    @property
    def operations(self):
        d = {
            "get": self.get,
            "put": self.put,
            "post": self.post,
            "delete": self.delete,
            "options": self.options,
            "head": self.head,
            "patch": self.patch,
            "trace": self.trace,
        }
        return {k: v for k, v in d.items() if v is not None}


class Components(BaseModel):
    schemas: Optional[Dict[str, JSchema]] = None
    responses: Optional[Dict[str, Response]] = None
    parameters: Optional[Dict[str, Parameter]] = None
    examples: Optional[Dict[str, Any]] = None
    requestBodies: Optional[Dict[str, RequestBody]] = None
    headers: Optional[Dict[str, Any]] = None
    securitySchemes: Optional[Dict[str, Any]] = None
    links: Optional[Dict[str, Any]] = None
    callbacks: Optional[Dict[str, Any]] = None
    pathItems: Optional[Dict[str, PathItem]] = None


BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class OpenAPI(BaseModel):
    openapi: str = Field(..., pattern=r"^3\.\d\.\d+(-.+)?$")
    info: Info
    jsonSchemaDialect: Optional[HttpUrl] = (
        "https://spec.openapis.org/oas/3.1/dialect/WORK-IN-PROGRESS"
    )
    servers: Optional[List[Server]] = [Server(url="/")]
    paths: Dict[str, Union[Reference, PathItem]] = {}
    webhooks: Optional[Dict[str, PathItem]] = None
    components: Optional[Components] = None
    security: Optional[List[Dict[str, List[str]]]] = None  # Refined to List of Dicts
    tags: Optional[List[Tag]] = None
    externalDocs: Optional[ExternalDocumentation] = None

    def get_operation_by_operationId(self, operationId: str) -> Operation | None:
        for path_item in self.paths.values():
            for op in path_item.operations.values():
                if op.operationId == operationId:
                    return op

    def resolve_ref(
        self, obj: Reference | BaseModelT | None, object_type: type[BaseModelT]
    ) -> BaseModelT | None:
        if isinstance(obj, Reference):
            tmp = find_ref(self.model_dump(), obj.ref)
            return object_type.model_validate(tmp)
        return obj

    def save(self, file_name: str):
        if file_name.endswith(".json"):
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(
                    self.model_dump_json(indent=2, by_alias=True, exclude_none=True)
                )
            return
        # TODO yaml
        raise NotImplementedError()


def read_openapi(file_path: str) -> OpenAPI:
    with open(file_path, "r") as file:
        if file_path.endswith("json"):
            d = json.load(file)
        else:
            d = yaml.safe_load(file)
    return OpenAPI.model_validate(d, strict=False)
