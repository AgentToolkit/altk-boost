import logging
from pathlib import Path
import base64
import datetime
import os
import tomli as tomllib
from typing import Any
from altk.build_time.test_case_generation_toolkit.src.toolops.exceptions import (
    ToolEnrichmentError,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.enrichment.mcp_cf_tool_enrichment.prompt_utils import (
    generate_enriched_tool_description,
)

logger = logging.getLogger(__name__)


class ToolOpsMCPCFToolEnrichment:
    def __init__(self, llm_client, gen_mode):
        self.llm_client = llm_client
        self.gen_mode = gen_mode
        self.sessionid = self._get_unique_sessionid()

        self.llm_config: dict[str, Any] = {}
        file_path = Path(__file__)
        absolute_path = file_path.resolve()
        cfg_file = absolute_path.parent / "conf/llm_config.toml"
        with Path(cfg_file).open(mode="rb") as task_file:
            self.llm_config = tomllib.load(task_file)

    def _get_unique_sessionid(self) -> str:
        timestamp = ""
        timestamp = datetime.datetime.now().strftime(
            "%Y-%m-%dT%H-%M-%S.%fZ-"
        ) + base64.urlsafe_b64encode(os.urandom(6)).decode("ascii")

        return timestamp

    async def enrich_mc_cf_tool(
        self,
        mcp_cf_toolspec: dict[str, Any],
        debug_mode: bool = False,
        logfolder: str = "log/",
    ) -> str:
        if (
            "name" not in mcp_cf_toolspec
            or "description" not in mcp_cf_toolspec
            or "inputSchema" not in mcp_cf_toolspec
        ):
            raise ToolEnrichmentError(error_message="Invalid MCP CF tool Spec")

        tool_name = mcp_cf_toolspec["name"]
        current_tool_description = ""
        if mcp_cf_toolspec["description"]:
            current_tool_description = mcp_cf_toolspec["description"]
        if current_tool_description:
            current_tool_description = current_tool_description.replace("\n", "\\n")
        input_schema = mcp_cf_toolspec["inputSchema"]
        if debug_mode:
            logfolder = "log/" + self.sessionid
            os.makedirs(logfolder, exist_ok=True)

        self.llm_config["llm_client"] = self.llm_client
        self.llm_config["gen_mode"] = self.gen_mode
        enriched_description = await generate_enriched_tool_description(
            tool_name,
            current_tool_description,
            input_schema,
            self.llm_config,
            logfolder,
            debug_mode,
        )
        return enriched_description
