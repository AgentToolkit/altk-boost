import ast
from altk.build_time.test_case_generation_toolkit.src.toolops.toolspec.tool_infos.ToolInfo import (
    ToolInfo,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.toolspec.tool_infos.Param import (
    Param,
)
import json
import logging
from altk.build_time.test_case_generation_toolkit.src.toolops.exceptions import (
    ToolCreationError,
)
import re
from altk.build_time.test_case_generation_toolkit.src.toolops.enrichment.python_tool_enrichment.enrichment_utils.tool.docstring_utils import (
    extract_from_python_code,
    is_google_format,
    convert_google_to_sphinx,
)
from docstring_parser import DocstringStyle, parse

logger = logging.getLogger("toolops.toolspec.populate_tool_info")


def flatten_attr(node):
    if isinstance(node, ast.Attribute):
        return str(flatten_attr(node.value)) + "." + node.attr
    elif isinstance(node, ast.Name):
        return str(node.id)
    else:
        return ""


def extract_function_names_with_decorators(
    tool_source_code1: str,
) -> list[str, list[str]]:
    """
    Extract function names and their decorators from Python source code.

    Args:
        source_code (str): Python source code as a string

    Returns:
        list[str, list[str]]: List of tuples when each tuple consists of function names and lists of its decorator names
    """
    try:
        # Parse the source code into an AST
        tree = ast.parse(tool_source_code1)

        # Dictionary to store function names and their decorators
        func_names_with_decorators = []

        # Traverse the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get function name
                function_name = node.name

                # Get decorators
                decorators = []
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Name):
                            decorators.append(decorator.func.id)
                        elif isinstance(decorator.func, ast.Attribute):
                            # Handle decorators like @abc.decorator4()
                            decorator_name = (
                                f"{decorator.func.value.id}.{decorator.func.attr}"
                            )
                            decorators.append(decorator_name)
                    elif isinstance(decorator, ast.Attribute):
                        # Handle decorators like @abc.decorator4 (without parentheses)
                        decorator_name = f"{decorator.value.id}.{decorator.attr}"
                        decorators.append(decorator_name)

                # Store in dictionary
                # functions[function_name] = decorators
                func_names_with_decorators.append((function_name, decorators))

    except SyntaxError as e:
        raise ValueError(f"Invalid Python code: {str(e)}") from e

    return func_names_with_decorators


def extract_elements(docstring_text):
    current_tool_description = ""
    docstring_params = []
    docstring_params_types = []
    docstring_params_desc = []
    return_description = ""
    long_description = ""  # Also extract long description if needed
    docstring_for_parsing = docstring_text  # Start with the full docstring

    if docstring_text:
        # --- Manual Extraction of Examples Section (before parsing) ---
        try:
            # Regex to find various example headings
            match = re.search(
                r"^\s*(?:Examples|Input Example|Example \d+|Example|Input Examples):\s*$(.*?)(?:^\s*\w+:|\Z)",
                docstring_text,
                re.MULTILINE | re.DOTALL | re.IGNORECASE,
            )
            if match:
                # Prepare the docstring for the parser by removing the example section
                docstring_for_parsing = docstring_text[: match.start()].rstrip()
        except Exception as e:
            print(f"Error during example extraction: {e}")
            # Proceed with parsing the original docstring if example extraction fails
            docstring_for_parsing = docstring_text

        # --- Parse the main docstring structure (without examples) ---
        try:
            # Parse using docstring-parser for reST/Sphinx style
            parsed = parse(docstring_for_parsing, style=DocstringStyle.REST)

            short_description = parsed.short_description
            current_tool_description = short_description or ""
            long_description = parsed.long_description or ""

            # Combine descriptions if long exists, otherwise use short
            if long_description:
                current_tool_description = (
                    f"{short_description}\n\n{long_description}".strip()
                )
            else:
                current_tool_description = parsed.short_description or ""
            current_tool_description = current_tool_description.strip()

            for param in parsed.params:
                docstring_params.append(param.arg_name)
                docstring_params_types.append(param.type_name or "")
                docstring_params_desc.append(param.description or "")

            if parsed.returns:
                return_description = parsed.returns.description or ""
                # Optionally include type name if needed:
                # if parsed.returns.type_name:
                #    return_description += f" (Type: {parsed.returns.type_name})"
        except Exception as e:
            print(f"Error parsing docstring: {e}")
        # Optionally return defaults or raise the exception

        # cleanup start

    if current_tool_description:
        current_tool_description = current_tool_description.replace('"""', "").strip()
    if return_description:
        return_description = return_description.replace('"""', "").strip()
        # cleanup end

    return (
        current_tool_description,
        docstring_params,
        docstring_params_types,
        docstring_params_desc,
        return_description,
    )


def parse_param_type(param_type_sig):
    required = True
    param_type = param_type_sig
    if param_type_sig.startswith("Optional"):
        required = False
        param_type = param_type_sig.split("Optional[")[1].split("]")[0]
    return param_type, required


def parse_python_tool(python_tool_str):
    try:
        toolinfo_obj = ToolInfo()
        toolinfo_obj.server = None
        toolinfo_obj.auth = None
        toolinfo_obj.security = None
        toolinfo_obj.output_schema = None
        toolinfo_obj.method = None
        toolinfo_obj.path = None
        toolinfo_obj.body = None
        function_names_with_decorators = extract_function_names_with_decorators(
            python_tool_str
        )
        method_name = ""
        for _, func_decorator in enumerate(function_names_with_decorators):
            if "tool" in func_decorator[1]:
                method_name = func_decorator[0]
                (
                    method_name,
                    parameters,
                    param_types,
                    method_body,
                    signature,
                    _,
                    _,
                    _,
                ) = extract_from_python_code(method_name, python_tool_str)
                toolinfo_obj.name = method_name
                docstring = method_body.split('"""')[1]
                if is_google_format(docstring):
                    docstring = convert_google_to_sphinx(docstring)
                (
                    current_tool_description,
                    docstring_params,
                    _,
                    docstring_params_desc,
                    _,
                ) = extract_elements(docstring)
                toolinfo_obj.description = current_tool_description
                for param in parameters:
                    param_obj = Param()
                    param_obj.name = param
                    param_obj.type, param_obj.required = parse_param_type(
                        param_types[parameters.index(param)]
                    )
                    if param in docstring_params:
                        param_obj.description = docstring_params_desc[
                            docstring_params.index(param)
                        ]
                    else:
                        param_obj.description = ""
                    if toolinfo_obj.queryParams:
                        toolinfo_obj.queryParams.append(param_obj)
                    else:
                        toolinfo_obj.queryParams = [param_obj]
                break
    except Exception as e:
        logger.error(
            "Problem in parsing python tool",
            extra={
                "details": json.dumps({"python_tool": python_tool_str, "error": str(e)})
            },
        )
        raise ToolCreationError(toolinfo_obj.name, str(e)) from e
    return toolinfo_obj
