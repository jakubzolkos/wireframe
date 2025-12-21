class WireframeError(Exception):
    """Base exception for Wireframe application."""
    pass

class PDFParsingError(WireframeError):
    """Raised when PDF parsing fails."""
    pass

class LLMContextLimitError(WireframeError):
    """Raised when LLM context limit is exceeded."""
    pass

class MissingVariableError(WireframeError):
    """Raised when required variables are missing for calculation."""
    def __init__(self, missing_vars: list[str]):
        self.missing_vars = missing_vars
        super().__init__(f"Missing variables: {', '.join(missing_vars)}")

