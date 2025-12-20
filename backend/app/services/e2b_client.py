import json
from e2b import Sandbox
from app.config import settings
from app.core.exceptions import ExecutionError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class E2BService:
    def __init__(self) -> None:
        self.api_key = settings.e2b_api_key

    async def execute_script(self, script: str, timeout: int = 30) -> dict[str, float]:
        try:
            await logger.ainfo("e2b_execution_start", script_length=len(script))
            async with Sandbox(api_key=self.api_key) as sandbox:
                result = await sandbox.run(script, timeout=timeout)
                stdout = result.stdout
                stderr = result.stderr

                if result.exit_code != 0:
                    await logger.aerror(
                        "e2b_execution_failed",
                        exit_code=result.exit_code,
                        stderr=stderr,
                    )
                    raise ExecutionError(f"Script execution failed: {stderr}", error_output=stderr)

                try:
                    output_data = json.loads(stdout)
                    if not isinstance(output_data, dict):
                        raise ValueError("Output must be a dictionary")
                    await logger.ainfo("e2b_execution_success", output_keys=list(output_data.keys()))
                    return output_data
                except json.JSONDecodeError as e:
                    await logger.aerror("e2b_output_parse_error", stdout=stdout, error=str(e))
                    raise ExecutionError(
                        f"Failed to parse JSON output: {stdout}",
                        error_output=stderr,
                    )
        except Exception as e:
            await logger.aerror("e2b_execution_error", error=str(e))
            raise ExecutionError(f"E2B execution error: {str(e)}") from e


e2b_service = E2BService()
