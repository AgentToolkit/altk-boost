from altk.build_time.test_case_generation_toolkit.src.toolops.validation.tool_analysis.tool_analysis_utils.analyse_events.langgraph_event_processing import (
    identify_error_taxonomy as langgraph_identify_error_taxonomy,
)

import logging

logger = logging.getLogger(__name__)


def get_error_taxonomy_recommendations(tool_name, test_cases_with_tool_execution):
    logger.info("Running error taxonomy and recommendations")
    try:
        logger.info("processing test case errors for langgraph framework")
        test_cases_with_error_taxonomy_recommendations = (
            langgraph_identify_error_taxonomy(test_cases_with_tool_execution)
        )
        return test_cases_with_error_taxonomy_recommendations
    except Exception as e:
        logger.info("Error in processing test case error taxonomy - " + str(e))
        return test_cases_with_tool_execution
