from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.exceptions import (
    EDAException,
    PDFParsingError,
    LLMContextLimitError,
    MissingVariableError,
    ExecutionError,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, PDFParsingError):
        await logger.aerror("pdf_parsing_error", error=exc.message, confidence=exc.confidence_score)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "PDF parsing failed",
                "message": exc.message,
                "confidence_score": exc.confidence_score,
            },
        )

    if isinstance(exc, LLMContextLimitError):
        await logger.aerror("llm_context_limit", error=exc.message, tokens=exc.token_count)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "LLM context limit exceeded",
                "message": exc.message,
                "token_count": exc.token_count,
            },
        )

    if isinstance(exc, MissingVariableError):
        await logger.aerror("missing_variables", error=exc.message, missing=exc.missing_variables)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Missing required variables",
                "message": exc.message,
                "missing_variables": exc.missing_variables,
            },
        )

    if isinstance(exc, ExecutionError):
        await logger.aerror("execution_error", error=exc.message, output=exc.error_output)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Code execution failed",
                "message": exc.message,
                "error_output": exc.error_output,
            },
        )

    if isinstance(exc, EDAException):
        await logger.aerror("eda_exception", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "EDA processing error", "message": str(exc)},
        )

    await logger.aerror("unhandled_exception", error=str(exc), exc_type=type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "message": "An unexpected error occurred"},
    )
