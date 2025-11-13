class ToolCreationError(Exception):
    def __init__(self, tool_name, error_message):
        super().__init__()
        self.error_message = error_message
        self.tool_name = tool_name

    def __str__(self):
        return (
            "Error in creating the tool - "
            + self.tool_name
            + " and the details are - "
            + self.error_message
        )


class ToolEnrichmentError(Exception):
    def __init__(self, tool_name, error_message):
        super().__init__()
        self.error_message = error_message
        self.tool_name = tool_name

    def __str__(self):
        return (
            "Error in enriching the tool - "
            + self.tool_name
            + " and the details are - "
            + self.error_message
        )


class TestCaseCreationError(Exception):
    def __init__(self, tool_name, error_message):
        super().__init__()
        self.error_message = error_message
        self.tool_name = tool_name

    def __str__(self):
        return (
            "Error in creating test cases - "
            + self.tool_name
            + " and the details are - "
            + self.error_message
        )


class NLTestCaseGenearationError(Exception):
    def __init__(self, tool_name, error_message):
        super().__init__()
        self.error_message = error_message
        self.tool_name = tool_name

    def __str__(self):
        return (
            "Error in generating NL test cases - "
            + self.tool_name
            + " and the details are - "
            + self.error_message
        )
