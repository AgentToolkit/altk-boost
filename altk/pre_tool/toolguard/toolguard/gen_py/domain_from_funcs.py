import os
from pathlib import Path
from typing import Callable, List
from os.path import join

from altk.pre_tool.toolguard.toolguard.gen_py.api_extractor import APIExtractor
from altk.pre_tool.toolguard.toolguard.common.str import to_camel_case, to_snake_case
from altk.pre_tool.toolguard.toolguard.data_types import FileTwin, RuntimeDomain
import altk.pre_tool.toolguard.toolguard.gen_py.consts as consts


def generate_domain_from_functions(
    py_path: str, app_name: str, funcs: List[Callable], include_module_roots: List[str]
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

    # APP init and Types
    os.makedirs(join(py_path, to_snake_case(app_name)), exist_ok=True)
    FileTwin(file_name=join(to_snake_case(app_name), "__init__.py"), content="").save(
        py_path
    )

    extractor = APIExtractor(py_path=py_path, include_module_roots=include_module_roots)
    api_cls_name = f"I_{to_camel_case(app_name)}"
    impl_module_name = to_snake_case(f"{app_name}.{app_name}_impl")
    impl_class_name = to_camel_case(f"{app_name}_Impl")
    api, types, impl = extractor.extract_from_functions(
        funcs,
        interface_name=api_cls_name,
        interface_module_name=to_snake_case(f"{app_name}.i_{app_name}"),
        types_module_name=to_snake_case(f"{app_name}.{app_name}_types"),
        impl_module_name=impl_module_name,
        impl_class_name=impl_class_name,
    )

    return RuntimeDomain(
        app_name=app_name,
        toolguard_common=common,
        app_types=types,
        app_api_class_name=api_cls_name,
        app_api=api,
        app_api_impl_class_name=impl_class_name,
        app_api_impl=impl,
        app_api_size=len(funcs),
    )
