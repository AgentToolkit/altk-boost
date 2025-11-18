import os
import json
import logging

from altk.build_time.test_case_generation_toolkit.src.toolops.validation.tool_analysis.tool_analysis_utils.analyse_events.error_processing import (
    get_error_taxonomy_recommendations,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.validation.tool_analysis.tool_analysis_utils.report_utils.report_processing import (
    get_final_report,
)

logger = logging.getLogger(__name__)
pwd = os.getcwd()


class ErrorAnalysis:
    def __init__(self, tool_name, test_cases_with_tool_execution):
        self.tool_name = tool_name
        self.test_cases_with_tool_execution = test_cases_with_tool_execution

    def get_tool_report(self, report_level="detailed"):
        logger.info(
            "Started test case analysis",
            extra={"details": json.dumps({"tool": self.tool_name})},
        )
        test_cases_with_error_taxonomy_recommendations = (
            get_error_taxonomy_recommendations(
                self.tool_name, self.test_cases_with_tool_execution
            )
        )
        logger.info(
            "Completed test case analysis",
            extra={"details": json.dumps({"tool": self.tool_name})},
        )
        logger.info(
            "Started report generation for tool",
            extra={"details": json.dumps({"tool": self.tool_name})},
        )
        final_report = get_final_report(
            test_cases_with_error_taxonomy_recommendations, self.tool_name, report_level
        )
        logger.info(
            "Successfully generated test case report for tool",
            extra={"details": json.dumps({"tool": self.tool_name})},
        )
        # return test_cases_with_error_taxonomy_recommendations,final_report
        return final_report


if __name__ == "__main__":
    test_data_path = os.path.join(pwd, "test_data", "test_case_execution")
    output_report_path = os.path.join(pwd, "test_data", "test_case_execution")
    tool_name, report_level = "getApiV2Tickets", "detailed"
    test_cases_with_tool_execution = json.load(
        open(
            os.path.join(
                test_data_path, tool_name + "_test_cases_with_tool_execution.json"
            )
        )
    )
    error_analysis = ErrorAnalysis(tool_name, test_cases_with_tool_execution)
    test_cases_with_error_taxonomy_recommendations, final_report = (
        error_analysis.get_tool_report(report_level)
    )
    with open(
        os.path.join(
            output_report_path,
            tool_name + "_test_cases_with_error_taxonomy_recommendations.json",
        ),
        "w",
    ) as ter:
        json.dump(test_cases_with_error_taxonomy_recommendations, ter, indent=2)
    ter.close()
    with open(
        os.path.join(output_report_path, tool_name + "_final_test_report.json"), "w"
    ) as fr:
        json.dump(final_report, fr, indent=2)
    fr.close()
    # print(final_report)
