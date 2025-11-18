from typing import Set
from altk.core.toolkit import AgentPhase
from altk.build_time.tool_enrichment_toolkit.core.toolkit import (
    ToolEnrichComponent,
    PythonToolEnrichBuildInput,
    PythonToolEnrichBuildOutput,
    MCPCFToolEnrichBuildInput,
    MCPCFToolEnrichBuildOutput,
)
from altk.build_time.tool_enrichment_toolkit.core.config import (
    PythonToolEnrichConfig,
    MCPCFToolEnrichConfig,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.enrichment.python_tool_enrichment.enrichment import (
    PythonToolOpsEnrichment,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.enrichment.mcp_cf_tool_enrichment.enrichment import (
    ToolOpsMCPCFToolEnrichment,
)


class PythonToolEnrichComponent(ToolEnrichComponent):
    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        return {AgentPhase.BUILDTIME}

    def _build(
        self, data: PythonToolEnrichBuildInput, config: PythonToolEnrichConfig
    ) -> PythonToolEnrichBuildOutput:  # type: ignore
        toolops_enrichment = PythonToolOpsEnrichment(
            llm_client=config.llm_client, gen_mode=config.gen_mode
        )
        import asyncio

        enriched_python_tool, _ = asyncio.run(
            toolops_enrichment.enrich_python_tool(
                python_tool_str=data.python_tool,
                enable_tool_description_enrichment=config.enable_tool_description_enrichment,
                enable_tool_parameter_description_enrichment=config.enable_tool_parameter_description_enrichment,
                enable_tool_return_description_enrichment=config.enable_tool_return_description_enrichment,
                enable_tool_example_enrichment=config.enable_tool_example_enrichment,
            )
        )
        return PythonToolEnrichBuildOutput(enriched_python_tool=enriched_python_tool)

    def process(
        self,
        data: PythonToolEnrichBuildInput,
        config: PythonToolEnrichConfig,
        phase: AgentPhase,
    ) -> dict:
        if phase not in self.supported_phases():
            raise ValueError(
                f"{self.__class__.__name__} does not support phase {phase}"
            )

        if phase == AgentPhase.BUILDTIME:
            return self._build(data, config)


class MCPCFToolEnrichComponent(ToolEnrichComponent):
    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        return {AgentPhase.BUILDTIME}

    def _build(
        self, data: MCPCFToolEnrichBuildInput, config: MCPCFToolEnrichConfig
    ) -> PythonToolEnrichBuildOutput:  # type: ignore
        toolops_enrichment = ToolOpsMCPCFToolEnrichment(
            llm_client=config.llm_client, gen_mode=config.gen_mode
        )
        import asyncio

        enriched_description = asyncio.run(
            toolops_enrichment.enrich_mc_cf_tool(mcp_cf_toolspec=data.mcp_cf_toolspec)
        )
        out_mcp_cf_toolspec = data.mcp_cf_toolspec.copy()
        out_mcp_cf_toolspec["description"] = enriched_description
        return MCPCFToolEnrichBuildOutput(mcp_cf_toolspec=out_mcp_cf_toolspec)

    def process(
        self,
        data: MCPCFToolEnrichBuildInput,
        config: MCPCFToolEnrichConfig,
        phase: AgentPhase,
    ) -> dict:
        if phase not in self.supported_phases():
            raise ValueError(
                f"{self.__class__.__name__} does not support phase {phase}"
            )

        if phase == AgentPhase.BUILDTIME:
            return self._build(data, config)
