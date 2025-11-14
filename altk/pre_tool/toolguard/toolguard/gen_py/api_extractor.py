from dataclasses import is_dataclass
from enum import Enum
import inspect
import os
import textwrap
from types import FunctionType, UnionType
import types
from typing import (
    Callable,
    DefaultDict,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    get_type_hints,
    get_origin,
    get_args,
)
from typing import Annotated, Union
from collections import defaultdict, deque
import typing
from altk.pre_tool.toolguard.toolguard.common.py import module_to_path, unwrap_fn
from altk.pre_tool.toolguard.toolguard.data_types import FileTwin

Dependencies = DefaultDict[type, Set[type]]


class APIExtractor:
    def __init__(self, py_path: str, include_module_roots: Optional[List[str]] = None):
        if not include_module_roots:
            include_module_roots = []
        self.py_path = py_path
        self.include_module_roots = include_module_roots

    def extract_from_functions(
        self,
        funcs: List[Callable],
        interface_name: str,
        interface_module_name: str,
        types_module_name: str,
        impl_module_name: str,
        impl_class_name: str,
    ) -> Tuple[FileTwin, FileTwin, FileTwin]:
        funcs = [unwrap_fn(func) for func in funcs]
        assert all([_is_global_or_class_function(func) for func in funcs])

        os.makedirs(self.py_path, exist_ok=True)

        # used types
        types = FileTwin(
            file_name=module_to_path(types_module_name),
            content=self._generate_types_file(
                *self._collect_all_types_from_functions(funcs)
            ),
        ).save(self.py_path)

        # API interface
        interface = FileTwin(
            file_name=module_to_path(interface_module_name),
            content=self._generate_interface_from_functions(
                funcs, interface_name, types_module_name
            ),
        ).save(self.py_path)

        # API impl interface
        impl = FileTwin(
            file_name=module_to_path(impl_module_name),
            content=self._generate_impl_from_functions(
                funcs,
                impl_class_name,
                interface_module_name,
                interface_name,
                types_module_name,
            ),
        ).save(self.py_path)

        return interface, types, impl

    def extract_from_class(
        self,
        typ: type,
        *,
        interface_name: Optional[str] = None,
        interface_module_name: Optional[str] = None,
        types_module_name: Optional[str] = None,
    ) -> Tuple[FileTwin, FileTwin]:
        """Extract interface and types from a class and save to files."""
        class_name = _get_type_name(typ)
        interface_name = interface_name or "I_" + class_name
        interface_module_name = interface_module_name or f"I_{class_name}".lower()
        types_module_name = types_module_name or f"{class_name}_types".lower()

        os.makedirs(self.py_path, exist_ok=True)

        # Types
        collected, dependencies = self._collect_all_types_from_class(typ)
        types_content = self._generate_types_file(collected, dependencies)
        types_file = module_to_path(types_module_name)
        types = FileTwin(file_name=types_file, content=types_content).save(self.py_path)

        # API interface
        if_content = self._generate_interface_from_class(
            typ, interface_name, types_module_name
        )
        if_file = module_to_path(interface_module_name)
        interface = FileTwin(file_name=if_file, content=if_content).save(self.py_path)

        return interface, types

    def _generate_interface_from_class(
        self, typ: type, interface_name: str, types_module: str
    ) -> str:
        # Start building the interface
        lines = [
            "# Auto-generated class interface",
            "from typing import *  # type: ignore",
            "from abc import ABC, abstractmethod",
            f"from {types_module} import *",
            "",
        ]

        lines.append(f"class {interface_name}(ABC):")  # Abstract class

        # Add class docstring if available
        if typ.__doc__:
            docstring = typ.__doc__.strip()
            if docstring:
                lines.append('    """')
                # Handle multi-line docstrings
                for line in docstring.split("\n"):
                    lines.append(f"    {line.strip()}")
                lines.append('    """')

        # Get all methods
        methods = []
        for name, method in inspect.getmembers(typ, predicate=inspect.isfunction):
            if not name.startswith("_"):
                methods.append((name, method))

        if not methods:
            lines.append("    pass")
        else:
            for method_name, method in methods:
                # Add method docstring and signature
                lines.append("    @abstractmethod")
                method_lines = self._get_function_with_docstring(method, method_name)
                lines.extend([line if line else "" for line in method_lines])
                lines.append("        ...")
                lines.append("")

        return textwrap.dedent("\n".join(lines))

    def _generate_interface_from_functions(
        self, funcs: List[Callable], interface_name: str, types_module: str
    ) -> str:
        lines = [
            "# Auto-generated class interface",
            "from typing import * # type: ignore",
            "from abc import ABC, abstractmethod",
            f"from {types_module} import *",
            "",
        ]

        lines.append(f"class {interface_name}(ABC):")  # Abstract class
        lines.append("")

        indent = " " * 4
        if not funcs:
            lines.append(f"{indent}pass")
        else:
            for func in funcs:
                # Add method docstring and signature
                lines.append(f"{indent}@abstractmethod")
                method_lines = self._get_function_with_docstring(
                    func, _get_type_name(func)
                )
                lines.extend([line if line else "" for line in method_lines])
                lines.append(f"{indent}{indent}...")
                lines.append("")

        if any(["Decimal" in line for line in lines]):
            lines.insert(2, "from decimal import Decimal")

        return "\n".join(lines)

    def _generate_impl_from_functions(
        self,
        funcs: List[Callable],
        class_name: str,
        interface_module_name: str,
        interface_name: str,
        types_module: str,
    ) -> str:
        lines = [
            "# Auto-generated class",
            "from typing import *",
            "from abc import ABC, abstractmethod",
            f"from {interface_module_name} import {interface_name}",
            f"from {types_module} import *",
            "",
            """class IToolInvoker(ABC):
    T = TypeVar("T")
    @abstractmethod
    def invoke(self, toolname: str, arguments: Dict[str, Any], model: Type[T])->T:
        ...""",
            "",
        ]

        lines.append(f"class {class_name}({interface_name}):")  # class
        lines.append("")
        lines.append("""    def __init__(self, delegate: IToolInvoker):
        self._delegate = delegate
    """)

        if not funcs:
            lines.append("    pass")
        else:
            for func in funcs:
                # Add method docstring and signature
                method_lines = self._get_function_with_docstring(
                    func, _get_type_name(func)
                )
                lines.extend([line if line else "" for line in method_lines])
                lines.extend(self._generate_delegate_code(func))
                lines.append("")

        if any(["Decimal" in line for line in lines]):
            lines.insert(2, "from decimal import Decimal")

        return "\n".join(lines)

    def _generate_delegate_code(self, func: Callable) -> List[str]:
        func_name = _get_type_name(func)
        indent = " " * 4 * 2
        sig = inspect.signature(func)
        ret = sig.return_annotation
        if ret is inspect._empty:
            ret_name = "None"
        elif hasattr(ret, "__name__"):
            ret_name = ret.__name__
        else:
            ret_name = str(ret)
        return [
            indent + "args = {k: v for k, v in locals().items() if k != 'self'}",
            indent + f"return self._delegate.invoke('{func_name}', args, {ret_name})",
        ]

    def _get_function_with_docstring(
        self, func: FunctionType, func_name: str
    ) -> List[str]:
        """Extract method signature with type hints and docstring."""
        lines = []

        # Get method signature
        method_signature = self._get_method_signature(func, func_name)
        lines.append(f"    {method_signature}:")

        # Add method docstring if available
        if func.__doc__:
            docstring = func.__doc__
            indent = " " * 8
            if docstring:
                lines.append(indent + '"""')
                lines.extend(docstring.strip("\n").split("\n"))
                lines.append(indent + '"""')

        return lines

    def should_include_type(self, typ: type) -> bool:
        if hasattr(typ, "__module__"):
            module_root = typ.__module__.split(".")[0]
            if module_root in self.include_module_roots:
                return True
        return any([self.should_include_type(arg) for arg in get_args(typ)])

    def _generate_class_definition(self, typ: type) -> List[str]:
        """Generate a class definition with its fields."""
        lines = []
        class_name = _get_type_name(typ)

        if is_dataclass(typ):
            lines.append("@dataclass")

        # Determine base classes
        bases = [_get_type_name(b) for b in _get_type_bases(typ)]
        inheritance = f"({', '.join(bases)})" if bases else ""
        lines.append(f"class {class_name}{inheritance}:")

        # #is Pydantic?
        # is_pydantic = False
        # for base in cls.__bases__:
        #     if hasattr(base, '__module__') and 'pydantic' in str(base.__module__):
        #         is_pydantic = True

        indent = " " * 4
        # Add class docstring if available
        if typ.__doc__:
            docstring = typ.__doc__
            if docstring:
                lines.append(f'{indent}"""')
                lines.extend(
                    [f"{indent}{line}" for line in docstring.strip("\n").split("\n")]
                )
                lines.append(f'{indent}"""')

        # Fields
        annotations = getattr(typ, "__annotations__", {})
        if annotations:
            field_descriptions = self._extract_field_descriptions(typ)
            for field_name, field_type in annotations.items():
                if field_name.startswith("_"):
                    continue

                # Handle optional field detection by default=None
                is_optional = False
                default_val = getattr(typ, field_name, ...)
                if default_val is None:
                    is_optional = True
                elif hasattr(typ, "__fields__"):
                    # Pydantic field with default=None
                    field_info = typ.__fields__.get(field_name)
                    if field_info and field_info.is_required() is False:
                        is_optional = True

                type_str = self._format_type(field_type)

                # Avoid wrapping Optional twice
                if is_optional:
                    origin = get_origin(field_type)
                    args = get_args(field_type)
                    already_optional = (
                        origin is typing.Union
                        and type(None) in args
                        or type_str.startswith("Optional[")
                    )
                    if not already_optional:
                        type_str = f"Optional[{type_str}]"

                # Check if we have a description for this field
                description = field_descriptions.get(field_name)

                # if description and is_pydantic:
                #     # Use Pydantic Field with description
                #     lines.append(f'    {field_name}: {type_str} = Field(description="{description}")')
                if description:
                    # Add description as comment for non-Pydantic classes
                    lines.append(f"{indent}{field_name}: {type_str}  # {description}")
                else:
                    # No description available
                    lines.append(f"{indent}{field_name}: {type_str}")

        # Enum
        elif issubclass(typ, Enum):
            if issubclass(typ, str):
                lines.extend(
                    [f'{indent}{entry.name} = "{entry.value}"' for entry in typ]
                )
            else:
                lines.extend([f"{indent}{entry.name} = {entry.value}" for entry in typ])

        else:
            lines.append(f"{indent}pass")

        return lines

    def _extract_field_descriptions(self, typ: type) -> Dict[str, str]:
        """Extract field descriptions from various sources."""
        descriptions = {}

        # Method 1: Check for Pydantic Field definitions
        if hasattr(typ, "__fields__"):  # Pydantic v1
            for field_name, field_info in typ.__fields__.items():
                if hasattr(field_info, "field_info") and hasattr(
                    field_info.field_info, "description"
                ):
                    descriptions[field_name] = field_info.field_info.description
                elif hasattr(field_info, "description") and field_info.description:
                    descriptions[field_name] = field_info.description

        # Method 2: Check for Pydantic v2 model fields
        if hasattr(typ, "model_fields"):  # Pydantic v2
            for field_name, field_info in typ.model_fields.items():
                if hasattr(field_info, "description") and field_info.description:
                    descriptions[field_name] = field_info.description

        # Method 3: Check class attributes for Field() definitions
        for attr_name in dir(typ):
            if not attr_name.startswith("_"):
                try:
                    attr_value = getattr(typ, attr_name)
                    # Check if it's a Pydantic Field
                    if hasattr(attr_value, "description") and attr_value.description:
                        descriptions[attr_name] = attr_value.description
                    elif hasattr(attr_value, "field_info") and hasattr(
                        attr_value.field_info, "description"
                    ):
                        descriptions[attr_name] = attr_value.field_info.description
                except Exception:
                    pass

        # Method 4: Parse class source for inline comments or docstrings
        try:
            source_lines = inspect.getsourcelines(typ)[0]
            current_field = None

            for line in source_lines:
                line = line.strip()

                # Look for field definitions with type hints
                if (
                    ":" in line
                    and not line.startswith("def ")
                    and not line.startswith("class ")
                ):
                    # Extract field name
                    field_part = line.split(":")[0].strip()
                    if " " not in field_part and field_part.isidentifier():
                        current_field = field_part

                # Look for comments on the same line or next line
                if "#" in line and current_field:
                    comment = line.split("#", 1)[1].strip()
                    if comment and current_field not in descriptions:
                        descriptions[current_field] = comment
                    current_field = None

        except Exception:
            pass

        # Method 5: Check for dataclass field descriptions
        if hasattr(typ, "__dataclass_fields__"):
            for field_name, field in typ.__dataclass_fields__.items():
                if hasattr(field, "metadata") and "description" in field.metadata:
                    descriptions[field_name] = field.metadata["description"]

        return descriptions

    def _get_method_signature(self, method: FunctionType, method_name: str):
        """Extract method signature with type hints."""
        try:
            sig = inspect.signature(method)
            # Get param hints
            try:
                param_hints = get_type_hints(method)
            except Exception:
                param_hints = {}

            params = []
            if not sig.parameters.get("self"):
                params.append("self")

            for param_name, param in sig.parameters.items():
                param_str = param_name

                # Add type annotation if available
                if param_name in param_hints:
                    type_str = self._format_type(param_hints[param_name])
                    param_str += f": {type_str}"
                elif param.annotation != param.empty:
                    param_str += f": {param.annotation}"

                # Add default value if present
                if param.default != param.empty:
                    if isinstance(param.default, str):
                        param_str += f' = "{param.default}"'
                    else:
                        param_str += f" = {repr(param.default)}"

                params.append(param_str)

            # Handle return type
            return_annotation = ""
            if "return" in param_hints:
                if param_hints["return"] is not type(None):
                    return_type = self._format_type(param_hints["return"])
                    return_annotation = f" -> {return_type}"
            elif sig.return_annotation != sig.empty:
                return_annotation = f" -> {sig.return_annotation}"

            params_str = ", ".join(params)
            return f"def {method_name}({params_str}){return_annotation}"

        except Exception:
            # Fallback for problematic signatures
            return f"def {method_name}(self, *args, **kwargs)"

    def _collect_all_types_from_functions(
        self, funcs: List[Callable]
    ) -> Tuple[Set[type], Dependencies]:
        processed_types = set()
        collected = set()
        dependencies = defaultdict(set)

        for func in funcs:
            for param, hint in get_type_hints(func).items():  # noqa: B007
                self._collect_types_recursive(
                    hint, processed_types, collected, dependencies
                )

        return collected, dependencies

    def _collect_all_types_from_class(
        self, typ: type
    ) -> Tuple[Set[type], Dependencies]:
        """Collect all types used in the class recursively."""
        visited = set()
        collected = set()
        dependencies = defaultdict(set)

        # Field types
        try:
            class_hints = get_type_hints(typ)
            for field, hint in class_hints.items():  # noqa: B007
                self._collect_types_recursive(hint, visited, collected, dependencies)
        except Exception:
            pass

        # Methods and param types
        for name, method in inspect.getmembers(typ, predicate=inspect.isfunction):  # noqa: B007
            try:
                method_hints = get_type_hints(method)
                for hint in method_hints.values():
                    self._collect_types_recursive(
                        hint, visited, collected, dependencies
                    )
            except Exception:
                pass

        # Also collect base class types
        for base in _get_type_bases(typ):
            self._collect_types_recursive(base, visited, collected, dependencies)

        return collected, dependencies

    def _collect_types_recursive(
        self, typ: type, visited: Set[type], acc: Set[type], dependencies: Dependencies
    ):
        """Recursively collect all types from a type hint."""
        visited.add(typ)

        if not self.should_include_type(typ):
            return

        acc.add(typ)
        origin = get_origin(typ)
        args = get_args(typ)

        # Type with generic arguments. eg: List[Person]
        if origin and args:
            for f_arg in args:
                self._collect_types_recursive(f_arg, visited, acc, dependencies)
                self._add_dependency(typ, f_arg, dependencies)
            return

        # If it's a custom class, try to get its type hints
        try:
            field_hints = typ.__annotations__  # direct fields
            for field_name, field_hint in field_hints.items():  # noqa: B007
                f_origin = get_origin(field_hint)
                if f_origin:
                    for f_arg in get_args(field_hint):
                        self._collect_types_recursive(f_arg, visited, acc, dependencies)
                        self._add_dependency(typ, f_arg, dependencies)
                else:
                    self._collect_types_recursive(
                        field_hint, visited, acc, dependencies
                    )
                    self._add_dependency(typ, field_hint, dependencies)

            for base in _get_type_bases(typ):  # Base classes
                self._collect_types_recursive(base, visited, acc, dependencies)
                self._add_dependency(typ, base, dependencies)
        except Exception:
            pass

    def _add_dependency(
        self, dependent_type: type, dependency_type: type, dependencies: Dependencies
    ):
        """Add a dependency relationship between types."""
        dep_name = _get_type_name(dependent_type)
        dep_on_name = _get_type_name(dependency_type)
        if dep_name != dep_on_name:
            dependencies[dependent_type].add(dependency_type)

        for arg in get_args(dependency_type):
            dependencies[dependent_type].add(arg)

    def _topological_sort_types(self, types: List[type], dependencies: Dependencies):
        """Sort types by their dependencies using topological sort."""
        # Create a mapping of type names to types for easier lookup
        type_map = {_get_type_name(t): t for t in types}

        # Build adjacency list and in-degree count
        adj_list = defaultdict(list)
        in_degree = defaultdict(int)

        # Initialize in-degree for all types
        for t in types:
            type_name = _get_type_name(t)
            if type_name not in in_degree:
                in_degree[type_name] = 0

        # Build the dependency graph
        for dependent_type in types:
            dependent_name = _get_type_name(dependent_type)
            for dependency_type in dependencies.get(dependent_type, set()):
                dependency_name = _get_type_name(dependency_type)
                if (
                    dependency_name in type_map
                ):  # Only consider types we're actually processing
                    adj_list[dependency_name].append(dependent_name)
                    in_degree[dependent_name] += 1

        # Kahn's algorithm for topological sorting
        queue = deque([name for name in in_degree if in_degree[name] == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(type_map[current])

            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If we couldn't sort all types, there might be circular dependencies
        # Add remaining types at the end
        sorted_names = {_get_type_name(t) for t in result}
        remaining = [t for t in types if _get_type_name(t) not in sorted_names]
        result.extend(remaining)

        return result

    def _generate_types_file(
        self, collected_types: Set[type], dependencies: Dependencies
    ) -> str:
        """Generate the types file content."""
        lines = []
        lines.append("# Auto-generated type definitions")
        lines.append("from datetime import date, datetime")
        lines.append("from enum import Enum")
        lines.append("from typing import *")
        lines.append("from pydantic import BaseModel, Field")
        lines.append("from dataclasses import dataclass")
        lines.append("")

        custom_classes = []
        for typ in collected_types:
            # Check if it's a class with attributes
            if hasattr(typ, "__annotations__") or (
                hasattr(typ, "__dict__")
                and any(
                    not callable(getattr(typ, attr, None))
                    for attr in dir(typ)
                    if not attr.startswith("_")
                )
            ):
                custom_classes.append(typ)
        custom_classes = self._topological_sort_types(custom_classes, dependencies)

        # Generate custom classes (sorted by dependency)
        for cls in custom_classes:
            class_def = self._generate_class_definition(cls)
            if class_def:  # Only add non-empty class definitions
                lines.extend(class_def)
                lines.append("")

        if any(["Decimal" in line for line in lines]):
            lines.insert(2, "from decimal import Decimal")

        return "\n".join(lines)

    def _format_type(self, typ: type) -> str:
        if typ is None:
            return "Any"

        # Unwrap Annotated[T, ...]
        origin = get_origin(typ)
        if origin is Annotated:
            typ = get_args(typ)[0]
            origin = get_origin(typ)

        # Literal
        if origin is Literal:
            args = get_args(typ)
            literals = ", ".join(repr(a) for a in args)
            return f"Literal[{literals}]"

        # Union (Optional or other)
        if origin is Union:
            args = get_args(typ)
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return f"Optional[{self._format_type(non_none[0])}]"
            else:
                inner = ", ".join(self._format_type(a) for a in args)
                return f"Union[{inner}]"

        if origin is UnionType:
            args = get_args(typ)
            return "| ".join(self._format_type(a) for a in args)

        # Generic containers
        if origin:
            args = get_args(typ)
            inner = ", ".join(self._format_type(a) for a in args)
            if inner:
                return f"{_get_type_name(origin)}[{inner}]"
            return _get_type_name(origin)

        # Simple type
        return _get_type_name(origin or typ)


def _get_type_name(typ) -> str:
    """Get a consistent name for a type object."""
    if hasattr(typ, "__name__"):
        return typ.__name__
    return str(typ)


def _get_type_bases(typ: type) -> List[type]:
    if hasattr(typ, "__bases__"):
        return typ.__bases__  # type: ignore
    return []


def _is_global_or_class_function(func):
    if not callable(func):
        return False

    # Reject lambdas
    if _get_type_name(func) == "<lambda>":
        return False

    # Static methods and global functions are of type FunctionType
    if isinstance(func, types.FunctionType):
        return True

    # Class methods are MethodType but have __self__ as the class, not instance
    if isinstance(func, types.MethodType):
        if inspect.isclass(func.__self__):
            return True  # classmethod
        else:
            return False  # instance method

    return False


# Example class for testing
if __name__ == "__main__":
    # from airline2.domains.airline.tools import AirlineTools
    # extractor = APIExtractor("output", include_module_roots = ["airline2"])
    # # interface_file, types_file = extractor.extract_from_class(AirlineTools, output_dir="output")
    # t = AirlineTools({})
    # interface_file, types_file = extractor.extract_from_functions([AirlineTools.book_reservation], "I_Tau", "my_app.i_tau", "my_app.tau_types")

    from appointment_app import lg_tools

    funcs = [
        lg_tools.add_user,
        lg_tools.add_payment_method,
        lg_tools.get_user_payment_methods,
        lg_tools.get_available_dr_specialties,
        lg_tools.search_doctors,
        lg_tools.search_available_appointments,
    ]
    extractor = APIExtractor("output", include_module_roots=["appointment_app"])
    interface, types_, impl = extractor.extract_from_functions(
        funcs,
        "I_Clinic",
        "clinic.i_clinic",
        "clinic.clinc_types",
        "clinic.clinic_impl",
        "ClinicImpl",
    )

    print(f"Interface saved to: {interface.file_name}")
    print(f"Types saved to: {types_.file_name}")
    print(f"Impl saved to: {impl.file_name}")
    print("Done")
