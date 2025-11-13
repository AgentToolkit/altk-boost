import json
import logging

logger = logging.getLogger("toolops.toolspec.populate_toolspec_from_toolinfo")


def populate_toolspec(tool_info_obj):
    try:
        toolspec = {}
        toolspec["name"] = tool_info_obj.name
        toolspec["description"] = tool_info_obj.description
        toolspec["permission"] = "NA"
        toolspec["input_schema"] = {}
        # if tool_info_obj.output_schema:
        toolspec["output_schema"] = {}
        toolspec["binding"] = {
            "python": {"function": tool_info_obj.name, "requirements": []}
        }
        required_list = []
        if tool_info_obj.queryParams:
            toolspec["input_schema"]["type"] = "object"
            toolspec["input_schema"]["properties"] = {}
            for param in tool_info_obj.queryParams:
                if param.required:
                    required_list.append(param.name)
                toolspec["input_schema"]["properties"][param.name] = {
                    "type": param.type,
                    "description": param.description,
                }
            toolspec["input_schema"]["required"] = required_list

    except Exception as e:
        logger.error(
            "Problem in populating tool_info_obj into toolspec",
            extra={
                "details": json.dumps({"tool_info_obj": tool_info_obj, "error": str(e)})
            },
        )
    return toolspec
