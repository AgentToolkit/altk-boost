import json
from typing import Any, Dict, List

from altk.pre_tool.toolguard.toolguard.tool_policy_extractor.text_tool_policy_generator import (
    ToolInfo,
)


class OASSummarizer:
    def __init__(self, oas: Dict[str, Any]):
        self.oas = oas
        self.components = oas.get("components", {}).get("schemas", {})

    def summarize(self) -> List[ToolInfo]:
        operations = []
        for path, methods in self.oas.get("paths", {}).items():
            for method, operation in methods.items():
                summary = self._format_operation(path, method, operation)
                tool_info = ToolInfo(
                    name=summary.get("name"),
                    description=summary.get("description"),
                    signature=summary.get("signature"),
                    parameters=summary.get("params"),
                    full_description=json.dumps(summary, indent=4),
                )
                operations.append(tool_info)
                operations.append(tool_info)
        return operations

    def _format_operation(
        self, path: str, method: str, operation: Dict[str, Any]
    ) -> Dict[str, Any]:
        operation_id = operation.get(
            "operationId", f"{method}_{path.strip('/').replace('/', '_')}"
        )
        class_name = operation_id
        description = operation.get("description", "")
        request_body = operation.get("requestBody", {})
        params = self._parse_request_body(request_body) if request_body else {}
        signature = self._generate_signature(
            class_name, params, operation.get("responses", {})
        )
        example = operation.get(
            "x-input-examples", []
        )  # self._generate_example(class_name, params)
        output_examples = operation.get(
            "x-output-examples", []
        )  # self._parse_response_examples(operation.get("responses", {}))

        return {
            "name": class_name,
            "signature": signature,
            "description": description,
            "params": params,
            "examples": [example],
            "output_examples": output_examples,
        }

    def _parse_request_body(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        content = request_body.get("content", {}).get("application/json", {})
        schema = self._resolve_ref(content.get("schema", {}))
        props = schema.get("properties", {})
        required = schema.get("required", [])
        params = {}
        for param_name, param_schema in props.items():
            resolved_schema = self._resolve_ref(param_schema)
            param_type = self._resolve_schema_type(resolved_schema)
            param_desc = resolved_schema.get("description", "")
            params[param_name] = {
                "type": param_type,
                "description": param_desc,
                "required": param_name in required,
            }
        return params

    # def _resolve_schema_type(self, schema: Dict[str, Any]) -> str:
    #     if "anyOf" in schema:
    #         return "Union[" + ", ".join(self._resolve_schema_type(s) for s in schema["anyOf"]) + "]"
    #     if "oneOf" in schema:
    #         return "Union[" + ", ".join(self._resolve_schema_type(s) for s in schema["oneOf"]) + "]"
    #     if "$ref" in schema:
    #         return self._resolve_schema_type(self._resolve_ref(schema))
    #     if schema.get("type") == "array":
    #         item_type = self._resolve_schema_type(schema.get("items", {}))
    #         return f"List[{item_type}]"
    #     if schema.get("type") == "object":
    #         return "Dict[str, Any]"
    #
    #     return {
    #         "string": "str",
    #         "integer": "int",
    #         "number": "float",
    #         "boolean": "bool",
    #         "object": "Dict[str, Any]",
    #     }.get(schema.get("type", "Any"), "Any")

    def _resolve_schema_type(self, schema: Dict[str, Any]) -> str:
        if "anyOf" in schema:
            return (
                "Union["
                + ", ".join(self._resolve_schema_type(s) for s in schema["anyOf"])
                + "]"
            )
        if "oneOf" in schema:
            return (
                "Union["
                + ", ".join(self._resolve_schema_type(s) for s in schema["oneOf"])
                + "]"
            )
        if "$ref" in schema:
            return self._resolve_schema_type(self._resolve_ref(schema))
        if schema.get("type") == "array":
            item_type = self._resolve_schema_type(schema.get("items", {}))
            return f"List[{item_type}]"
        if schema.get("type") == "object":
            return "Dict[str, Any]"

        type_value = schema.get("type", "Any")
        if isinstance(type_value, list):
            # Filter out "null" and resolve remaining types
            non_null_types = [t for t in type_value if t != "null"]
            if not non_null_types:
                return "Optional[Any]"
            if len(non_null_types) == 1:
                base_type = self._resolve_schema_type(
                    {**schema, "type": non_null_types[0]}
                )
            else:
                base_type = (
                    "Union["
                    + ", ".join(
                        self._resolve_schema_type({"type": t}) for t in non_null_types
                    )
                    + "]"
                )
            return f"Optional[{base_type}]" if "null" in type_value else base_type

        return {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "object": "Dict[str, Any]",
        }.get(type_value, "Any")

    def _resolve_ref(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(schema, Dict):
            if "$ref" in schema:
                ref_path = schema["$ref"]
                if ref_path.startswith("#/components/schemas/"):
                    key = ref_path.split("/")[-1]
                    return self.components.get(key, {})
            return schema
        return schema

    def _generate_signature(
        self, class_name: str, params: Dict[str, Any], responses: Dict[str, Any]
    ) -> str:
        args = ", ".join(f"{name}: {meta['type']}" for name, meta in params.items())
        out = "str"
        if responses and "200" in responses:
            content = responses["200"]["content"]
            app_json = content.get("application/json", {})
            schema = self._resolve_ref(app_json.get("schema", {}))
            out = self._resolve_schema_type(schema)
        return f"{class_name}({args}) -> {out}"

    def _generate_example(self, class_name: str, params: Dict[str, Any]) -> str:
        args = ", ".join(
            '"example_string"' if meta["type"].startswith("str") else "0"
            for _, meta in params.items()
        )
        return f"{class_name}({args})"

    def _parse_response_examples(self, responses: Dict[str, Any]) -> List[str]:
        examples = []
        for response in responses.values():
            content = response.get("content", {})
            app_json = content.get("application/json", {})
            schema = self._resolve_ref(app_json.get("schema", {}))

            if "example" in app_json:
                example_data = app_json["example"]
            elif "examples" in app_json:
                example_data = next(iter(app_json["examples"].values()), {}).get(
                    "value"
                )
            else:
                example_data = self._construct_example_from_schema(schema)

            if example_data is not None:
                try:
                    examples.append(json.dumps(example_data))
                except Exception:
                    examples.append(str(example_data))
        return examples

    def _construct_example_from_schema(self, schema: Dict[str, Any]) -> Any:
        schema = self._resolve_ref(schema)
        if not isinstance(schema, Dict):
            return schema
        schema_type = schema.get("type")

        if schema_type == "object":
            if "additionalProperties" in schema:
                value_schema = self._resolve_ref(schema["additionalProperties"])
                return {
                    "example_key": self._construct_example_from_schema(value_schema)
                }
            props = schema.get("properties", {})
            return {
                key: self._construct_example_from_schema(self._resolve_ref(subschema))
                for key, subschema in props.items()
            }

        if schema_type == "array":
            item_schema = self._resolve_ref(schema.get("items", {}))
            return [self._construct_example_from_schema(item_schema)]

        if schema_type == "string":
            return schema.get("example", "example_string")
        if schema_type == "integer":
            return schema.get("example", 42)
        if schema_type == "number":
            return schema.get("example", 3.14)
        if schema_type == "boolean":
            return schema.get("example", True)

        if "anyOf" in schema:
            return self._construct_example_from_schema(schema["anyOf"][0])
        if "oneOf" in schema:
            return self._construct_example_from_schema(schema["oneOf"][0])
        if "allOf" in schema:
            return self._construct_example_from_schema(schema["allOf"][0])

        return "example_value"


if __name__ == "__main__":
    oas_file = (
        "/Users/naamazwerdling/Documents/OASB/policy_validation/airline/oas2.json"
    )
    # oas_file = "/Users/naamazwerdling/Documents/OASB/policy_validation/orca/bank/oas.json"
    shortfile = "/Users/naamazwerdling/Documents/OASB/policy_validation/airline/s1.json"
    # shortfile = "/Users/naamazwerdling/Documents/OASB/policy_validation/orca/bank/short.json"
    with open(oas_file) as f:
        oas_data = json.load(f)

    summarizer = OASSummarizer(oas_data)
    summary = summarizer.summarize()
    with open(shortfile, "w") as outfile:
        json.dump(summary, outfile, indent=4)

    print(json.dumps(summary, indent=2))
