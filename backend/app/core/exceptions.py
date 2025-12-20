class EDAException(Exception):
    pass


class PDFParsingError(EDAException):
    def __init__(self, message: str, confidence_score: float | None = None):
        self.message = message
        self.confidence_score = confidence_score
        super().__init__(self.message)


class LLMContextLimitError(EDAException):
    def __init__(self, message: str, token_count: int | None = None):
        self.message = message
        self.token_count = token_count
        super().__init__(self.message)


class MissingVariableError(EDAException):
    def __init__(self, message: str, missing_variables: list[str]):
        self.message = message
        self.missing_variables = missing_variables
        super().__init__(self.message)


class ExecutionError(EDAException):
    def __init__(self, message: str, error_output: str | None = None):
        self.message = message
        self.error_output = error_output
        super().__init__(self.message)
