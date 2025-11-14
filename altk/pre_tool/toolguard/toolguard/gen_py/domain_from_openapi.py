import os
from pathlib import Path
from typing import List, Optional, Tuple, Union
from os.path import join

from altk.pre_tool.toolguard.toolguard.common.array import find
from altk.pre_tool.toolguard.toolguard.common.py import module_to_path
from altk.pre_tool.toolguard.toolguard.common.str import to_camel_case, to_snake_case
import altk.pre_tool.toolguard.toolguard.gen_py.consts as consts
from altk.pre_tool.toolguard.toolguard.gen_py.templates import load_template
from altk.pre_tool.toolguard.toolguard.gen_py.utils.datamodel_codegen import (
    run as dm_codegen,
)
from altk.pre_tool.toolguard.toolguard.common.open_api import (
    OpenAPI,
    Operation,
    Parameter,
    ParameterIn,
    PathItem,
    Reference,
    RequestBody,
    Response,
    JSchema,
    read_openapi,
)
from altk.pre_tool.toolguard.toolguard.data_types import FileTwin, RuntimeDomain


def generate_domain_from_openapi(
    py_path: str, app_name: str, openapi_file: str
) -> RuntimeDomain:
    # ToolGuard Runtime
    os.makedirs(join(py_path, consts.RUNTIME_PACKAGE_NAME), exist_ok=True)

    root = str(Path(__file__).parent.parent)
    common = FileTwin.load_from(root, "data_types.py").save_as(
        py_path, join(consts.RUNTIME_PACKAGE_NAME, consts.RUNTIME_TYPES_PY)
    )
    runtime = FileTwin.load_from(root, "runtime.py")
    runtime.content = runtime.content.replace(
        "toolguard.", f"{consts.RUNTIME_PACKAGE_NAME}."
    )
    runtime.save_as(py_path, join(consts.RUNTIME_PACKAGE_NAME, consts.RUNTIME_INIT_PY))

    # APP Types
    oas = read_openapi(openapi_file)
    os.makedirs(join(py_path, to_snake_case(app_name)), exist_ok=True)

    types_name = f"{app_name}_types"
    types_module_name = f"{app_name}.{types_name}"
    types = FileTwin(
        file_name=module_to_path(types_module_name), content=dm_codegen(openapi_file)
    ).save(py_path)

    # APP Init
    FileTwin(
        file_name=join(to_snake_case(app_name), "__init__.py"),
        content=f"from . import {types_name}",
    ).save(py_path)

    # APP API
    api_cls_name = to_camel_case("I " + app_name)
    methods = _get_oas_methods(oas)
    api_module_name = to_snake_case(f"{app_name}.i_{app_name}")
    api = FileTwin(
        file_name=module_to_path(api_module_name),
        content=_generate_api(methods, api_cls_name, types_module_name),
    ).save(py_path)

    # APP API Impl
    impl_cls_name = to_camel_case(app_name + " impl")
    impl_module_name = to_snake_case(f"{app_name}.{app_name}_impl")
    cls_str = _generate_api_impl(
        methods, api_module_name, types_module_name, api_cls_name, impl_cls_name
    )
    api_impl = FileTwin(
        file_name=module_to_path(impl_module_name), content=cls_str
    ).save(py_path)

    return RuntimeDomain(
        app_name=app_name,
        toolguard_common=common,
        app_types=types,
        app_api_class_name=api_cls_name,
        app_api=api,
        app_api_impl_class_name=impl_cls_name,
        app_api_impl=api_impl,
        app_api_size=len(methods),
    )


def _get_oas_methods(oas: OpenAPI):
    methods = []
    for path, path_item in oas.paths.items():  # noqa: B007
        path_item = oas.resolve_ref(path_item, PathItem)
        assert path_item
        for mtd, op in path_item.operations.items():  # noqa: B007
            op = oas.resolve_ref(op, Operation)
            if not op:
                continue
            params = (path_item.parameters or []) + (op.parameters or [])
            params = [oas.resolve_ref(p, Parameter) for p in params]
            args, ret = _make_signature(op, params, oas)  # type: ignore
            args_str = ", ".join(["self"] + [f"{arg}:{type}" for arg, type in args])
            sig = f"({args_str})->{ret}"

            body = "pass"
            # if orign_funcs:
            #     func = find(orign_funcs or [], lambda fn: fn.__name__ == op.operationId) # type: ignore
            #     if func:
            #         body = _call_fn_body(func)
            methods.append(
                {
                    "name": to_snake_case(op.operationId),  # type: ignore
                    "signature": sig,
                    "doc": op.description,
                    "body": body,
                }
            )
    return methods


# def _call_fn_body(func:Callable):
#     module = inspect.getmodule(func)
#     if module is None or not hasattr(module, '__file__'):
#         raise ValueError("Function must be from an importable module")

#     module_name = module.__name__
#     qualname = func.__qualname__
#     func_name = func.__name__
#     parts = qualname.split('.')

#     if len(parts) == 1: # Regular function
#         return f"""
#     mod = importlib.import_module("{module_name}")
#     func = getattr(mod, "{func_name}")
#     return func(locals())"""

#     if len(parts) == 2:  # Classmethod or staticmethod
#         class_name = parts[0]
#         return f"""
#     mod = importlib.import_module("{module_name}")
#     cls = getattr(mod, "{class_name}")
#     func = getattr(cls, "{func_name}")
#     return func(locals())"""

#     if len(parts) > 2: # Instance method
#         class_name = parts[-2]
#         return f"""
#     mod = importlib.import_module("{module_name}")
#     cls = getattr(mod, "{class_name}")
#     instance = cls()
#     func = getattr(instance, "{func_name}")
#     return func(locals())"""
#     raise NotImplementedError("Unsupported function type or nested depth")


def _generate_api(methods: List, cls_name: str, types_module: str) -> str:
    return load_template("api.j2").render(
        types_module=types_module, class_name=cls_name, methods=methods
    )


def _generate_api_impl(
    methods: List, api_module: str, types_module: str, api_cls_name: str, cls_name: str
) -> str:
    return load_template("api_impl.j2").render(
        api_cls_name=api_cls_name,
        types_module=types_module,
        api_module=api_module,
        class_name=cls_name,
        methods=methods,
    )


def _make_signature(
    op: Operation, params: List[Parameter], oas: OpenAPI
) -> Tuple[Tuple[str, str], str]:
    fn_name = to_camel_case(op.operationId)
    args = []

    for param in params:
        if param.in_ == ParameterIn.path:
            args.append((param.name, _oas_to_py_type(param.schema_, oas) or "Any"))

    if find(params, lambda p: p.in_ == ParameterIn.query):
        query_type = f"{fn_name}ParametersQuery"
        args.append(("args", query_type))

    req_body = oas.resolve_ref(op.requestBody, RequestBody)
    if req_body:
        scm_or_ref = req_body.content_json.schema_
        body_type = _oas_to_py_type(scm_or_ref, oas)
        if body_type is None:
            body_type = f"{fn_name}Request"
        args.append(("args", body_type))

    rsp_or_ref = op.responses.get("200")
    rsp = oas.resolve_ref(rsp_or_ref, Response)
    if rsp:
        scm_or_ref = rsp.content_json.schema_
        if scm_or_ref:
            rsp_type = _oas_to_py_type(scm_or_ref, oas)
            if rsp_type is None:
                rsp_type = f"{fn_name}Response"

    return args, rsp_type


def _oas_to_py_type(scm_or_ref: Union[Reference, JSchema], oas: OpenAPI) -> str | None:
    if isinstance(scm_or_ref, Reference):
        return scm_or_ref.ref.split("/")[-1]

    scm = oas.resolve_ref(scm_or_ref, JSchema)
    if scm:
        py_type = _primitive_jschema_types_to_py(scm.type, scm.format)
        if py_type:
            return py_type
        # if scm.type == JSONSchemaTypes.array and scm.items:
        #     return f"List[{oas_to_py_type(scm.items, oas) or 'Any'}]"


def _primitive_jschema_types_to_py(
    type: Optional[str], format: Optional[str]
) -> Optional[str]:
    # https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.2.md#data-types
    if type == "string":
        if format == "date":
            return "datetime.date"
        if format == "date-time":
            return "datetime.datetime"
        if format in ["byte", "binary"]:
            return "bytes"
        return "str"
    if type == "integer":
        return "int"
    if type == "number":
        return "float"
    if type == "boolean":
        return "bool"
    return None
