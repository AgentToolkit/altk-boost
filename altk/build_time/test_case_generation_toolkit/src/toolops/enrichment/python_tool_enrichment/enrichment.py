import logging
from pathlib import Path
from typing import Any
import aiofiles
import yaml
import tomli as tomllib

from altk.build_time.test_case_generation_toolkit.src.toolops.enrichment.python_tool_enrichment.enrichment_utils.tool.service import (
    enrich_tool,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.enrichment.python_tool_enrichment.enrichment_utils.tool.utils import (
    ToolEnrichmentConfig,
    ToolEnrichmentOptions,
    ToolInputDetails,
    ToolLLMConfig,
    ToolOutputConfig,
    ToolUserInput,
    get_unique_sessionid,
    has_function_with_decorator,
)

logger = logging.getLogger(__name__)


class PythonToolOpsEnrichment:
    def __init__(self, llm_client, gen_mode):
        self.llm_client = llm_client
        self.gen_mode = gen_mode
        self.sessionid = get_unique_sessionid()
        self.llm_config = {}
        file_path = Path(__file__)
        absolute_path = file_path.resolve()
        cfg_file = absolute_path.parent / "enrichment_utils/conf/llm_config.toml"
        with Path(cfg_file).open(mode="rb") as task_file:
            self.llm_config = tomllib.load(task_file)

    async def enrich_python_tool(
        self,
        python_tool_str: str,
        enable_tool_description_enrichment: bool,
        enable_tool_parameter_description_enrichment: bool,
        enable_tool_return_description_enrichment: bool,
        enable_tool_example_enrichment: bool,
    ):
        options = {}
        options["tool_enrichment"] = {}
        options["tool_enrichment"]["enable_tool_description_enrichment"] = (
            enable_tool_description_enrichment
        )
        options["tool_enrichment"]["enable_tool_parameter_description_enrichment"] = (
            enable_tool_parameter_description_enrichment
        )
        options["tool_enrichment"]["enable_tool_return_description_enrichment"] = (
            enable_tool_return_description_enrichment
        )
        options["tool_enrichment"]["enable_tool_example_enrichment"] = (
            enable_tool_example_enrichment
        )
        return await self.do_enrichment(
            input_file_contents=python_tool_str, options=options
        )

    async def do_enrichment(
        self,
        input_file_contents: str,
        options: dict[str, Any],
        logfolder: str = "",
        kind: str = "python",
        debug_mode: bool = False,
        input_filename: str = "",
        iterative_mode=False,
        enrichment_type="",
        user_feedback: dict[str, Any] | None = None,
    ) -> tuple[str, dict]:
        if not options:
            file_path = Path(__file__)
            absolute_path = file_path.resolve()
            cfg_file = (
                absolute_path.parent
                / "enrichment_utils/conf/wxo_enrichment_config.yaml"
            )
            print("cfg_file: " + str(cfg_file))
            async with aiofiles.open(cfg_file) as f:
                content = await f.read()
                options = yaml.safe_load(content)

        enrichment_info: dict[str, Any] = {}
        enriched_file_contents: str = ""

        prompts_folder = logfolder + "/debug_enrichment/"
        if debug_mode:
            Path(prompts_folder).mkdir(parents=True, exist_ok=True)

        if kind == "python":
            if "tool_enrichment" not in options:
                print(
                    "tool_enrichment key not found in input cfg file!",
                )
                enrichment_info["error"] = (
                    "tool_enrichment key not found in input cfg file!"
                )

            if not has_function_with_decorator(input_file_contents, "tool"):
                print(
                    "Invalid python tool file as it does not have a function with @tool decorator"
                )
                enrichment_info["error"] = (
                    "Invalid python tool file as it does not have a function with @tool decorator. inp_file: "
                    + input_file_contents
                )
            else:
                tool_en_options = ToolEnrichmentOptions(**options["tool_enrichment"])

                if input_filename:
                    tool_name_mod = "".join(
                        char for char in input_filename if char.isalnum()
                    )
                    prefix = tool_name_mod
                else:
                    prefix = "python_tool"

                toolfile = input_filename if input_filename else "python_tool.py"
                input_details = ToolInputDetails(
                    tool_source_code=input_file_contents,
                    options=tool_en_options,
                    prefix=prefix,
                    tools_file=toolfile,
                )
                output_config = ToolOutputConfig(
                    logfolder=logfolder,
                    prompts_log_folder=prompts_folder,
                    debug_mode=debug_mode,
                )
                tool_llm_config = ToolLLMConfig(
                    llm_client=self.llm_client,
                    gen_mode=self.gen_mode,
                    llm_config=self.llm_config,
                )

                user_input = ToolUserInput(
                    iterative_mode=iterative_mode,
                    user_feedback=user_feedback,
                    enrichment_type=enrichment_type,
                )

                enrich_cfg = ToolEnrichmentConfig(
                    input_details=input_details,
                    user_input=user_input,
                    output_config=output_config,
                    tool_llm_config=tool_llm_config,
                )

                enriched_code, _, enrichments, original_filename_fullpath = enrich_tool(
                    enrich_cfg
                )

                enriched_file_contents = enriched_code
                enrichment_info["enrichments"] = enrichments
                enrichment_info["original_filename_fullpath"] = (
                    original_filename_fullpath
                )
        else:
            enrichment_info["error"] = (
                f"Invalid kind value: {kind}. It needs to be 'python''"
            )

        # return enriched_filename_fullpath, enrichment_info
        return enriched_file_contents, enrichment_info
