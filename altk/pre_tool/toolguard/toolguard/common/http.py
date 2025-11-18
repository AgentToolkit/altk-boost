from enum import Enum
from functools import cache
from typing import List


MEDIA_TYPE_APP_JSON = "application/json"
MEDIA_TYPE_MULTIPART_FORM = "multipart/form-data"
MEDIA_TYPE_APP_FORM = "application/x-www-form-urlencoded"


class StrEnum(str, Enum):
    """An abstract base class for string-based enums."""

    pass


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

    def __eq__(self, value: object) -> bool:
        return str(value).upper() == self.value

    def __ne__(self, value: object) -> bool:
        return not self.__eq__(value)

    def __hash__(self):
        return self.value.__hash__()

    @classmethod
    @cache
    def list(cls) -> List["HttpMethod"]:
        return list(map(lambda c: c.value, cls))


def is_valid_http_method(val: str):
    return val and val.upper() in HttpMethod.list()


PARAM_API_KEY = "api_key"

AUTH_HEADER = "Authorization"

SECURITY_COMPONENT_TYPE_API_KEY = "apiKey"
SECURITY_COMPONENT_SCHEME_BEARER = "bearer"
SECURITY_COMPONENT_SCHEME_BASIC = "basic"

SECURITY_COMPONENT_BEARER = {
    "type": "http",
    "scheme": SECURITY_COMPONENT_SCHEME_BEARER,
    "bearerFormat": "JWT",
}
