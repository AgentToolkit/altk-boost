import inspect
import json
import os
from types import ModuleType
from typing import Any, Dict, List, Optional, Type, Callable, TypeVar
from pydantic import BaseModel
import importlib.util

import functools
from .data_types import API_PARAM, RESULTS_FILENAME, FileTwin, RuntimeDomain, ToolPolicy

from abc import ABC, abstractmethod


class IToolInvoker(ABC):
    T = TypeVar("T")

    @abstractmethod
    def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]
    ) -> T: ...


def load_toolguards(
    directory: str, filename: str = RESULTS_FILENAME
) -> "ToolguardRuntime":
    full_path = os.path.join(directory, filename)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    result = ToolGuardsCodeGenerationResult(**data)
    return ToolguardRuntime(result, directory)


class ToolGuardCodeResult(BaseModel):
    tool: ToolPolicy
    guard_fn_name: str
    guard_file: FileTwin
    item_guard_files: List[FileTwin | None]
    test_files: List[FileTwin | None]


class ToolGuardsCodeGenerationResult(BaseModel):
    root_dir: str
    domain: RuntimeDomain
    tools: Dict[str, ToolGuardCodeResult]

    def save(
        self, directory: str, filename: str = RESULTS_FILENAME
    ) -> "ToolGuardsCodeGenerationResult":
        full_path = os.path.join(directory, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2)
        return self


class ToolguardRuntime:
    def __init__(self, result: ToolGuardsCodeGenerationResult, ctx_dir: str) -> None:
        self._ctx_dir = ctx_dir
        self._result = result
        self._guards = {}
        for tool_name, tool_result in result.tools.items():
            module = load_module_from_path(tool_result.guard_file.file_name, ctx_dir)
            guard_fn = find_function_in_module(module, tool_result.guard_fn_name)
            assert guard_fn, "Guard not found"
            self._guards[tool_name] = guard_fn

    def _make_args(
        self, guard_fn: Callable, args: dict, delegate: IToolInvoker
    ) -> Dict[str, Any]:
        sig = inspect.signature(guard_fn)
        guard_args = {}
        for p_name, param in sig.parameters.items():
            if p_name == API_PARAM:
                module = load_module_from_path(
                    self._result.domain.app_api_impl.file_name, self._ctx_dir
                )
                clazz = find_class_in_module(
                    module, self._result.domain.app_api_impl_class_name
                )
                assert clazz, (
                    f"class {self._result.domain.app_api_impl_class_name} not found in {self._result.domain.app_api_impl.file_name}"
                )
                guard_args[p_name] = clazz(delegate)
            else:
                arg = args.get(p_name)
                if inspect.isclass(param.annotation) and issubclass(
                    param.annotation, BaseModel
                ):
                    guard_args[p_name] = param.annotation.model_construct(**arg)
                else:
                    guard_args[p_name] = arg
        return guard_args

    def check_toolcall(self, tool_name: str, args: dict, delegate: IToolInvoker):
        guard_fn = self._guards.get(tool_name)
        if guard_fn is None:  # No guard assigned to this tool
            return
        guard_fn(**self._make_args(guard_fn, args, delegate))


def file_to_module(file_path: str):
    return file_path.removesuffix(".py").replace("/", ".")


def load_module_from_path(file_path: str, py_root: str) -> ModuleType:
    full_path = os.path.abspath(os.path.join(py_root, file_path))
    if not os.path.exists(full_path):
        raise ImportError(f"Module file does not exist: {full_path}")

    module_name = file_to_module(file_path)

    spec = importlib.util.spec_from_file_location(module_name, full_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec from {full_path}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore
    except Exception as e:
        raise ImportError(f"Failed to execute module '{module_name}': {e}") from e

    return module


def find_function_in_module(module: ModuleType, function_name: str):
    func = getattr(module, function_name, None)
    if func is None or not inspect.isfunction(func):
        raise AttributeError(
            f"Function '{function_name}' not found in module '{module.__name__}'"
        )
    return func


def find_class_in_module(module: ModuleType, class_name: str) -> Optional[Type]:
    cls = getattr(module, class_name, None)
    if isinstance(cls, type):
        return cls
    return None


T = TypeVar("T")


def guard_methods(obj: T, guards_folder: str) -> T:
    """Wraps all public bound methods of the given instance using the given wrapper."""
    for attr_name in dir(obj):
        if attr_name.startswith("_"):
            continue
        attr = getattr(obj, attr_name)
        if callable(attr):
            wrapped = guard_before_call(guards_folder)(attr)
            setattr(obj, attr_name, wrapped)
    return obj


class ToolMethodsInvoker(IToolInvoker):
    def __init__(self, object: object) -> None:
        self._obj = object

    def invoke(self, toolname: str, arguments: Dict[str, Any], model: Type[T]) -> T:
        mtd = getattr(self._obj, toolname)
        assert callable(mtd), f"Tool {toolname} was not found"
        return mtd(**arguments)


class ToolFunctionsInvoker(IToolInvoker):
    def __init__(self, funcs: List[Callable]) -> None:
        self._funcs_by_name = {func.__name__: func for func in funcs}

    def invoke(self, toolname: str, arguments: Dict[str, Any], model: Type[T]) -> T:
        func = self._funcs_by_name.get(toolname)
        assert callable(func), f"Tool {toolname} was not found"
        return func(**arguments)


def guard_before_call(guards_folder: str) -> Callable[[Callable], Callable]:
    """Decorator factory that logs function calls to the given logfile."""
    toolguards = load_toolguards(guards_folder)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            toolguards.check_toolcall(
                func.__name__, kwargs, ToolMethodsInvoker(func.__self__)
            )
            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
