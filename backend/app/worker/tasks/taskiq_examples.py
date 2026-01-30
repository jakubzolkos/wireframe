"""Example Taskiq tasks."""

import asyncio
import logging
from typing import Any

from app.worker.taskiq_app import broker

logger = logging.getLogger(__name__)


@broker.task
async def example_task(message: str) -> dict[str, Any]:
    """
    Example async task that processes a message.

    Args:
        message: Message to process

    Returns:
        Result dictionary with processed message
    """
    logger.info(f"Processing message: {message}")

    # Simulate async work
    await asyncio.sleep(1)

    result = {
        "status": "completed",
        "message": f"Processed: {message}",
    }
    logger.info(f"Task completed: {result}")
    return result


@broker.task
async def long_running_task(duration: int = 10) -> dict[str, Any]:
    """
    Example long-running async task.

    Args:
        duration: Duration in seconds

    Returns:
        Result dictionary
    """
    logger.info(f"Starting long-running task for {duration} seconds")

    for i in range(duration):
        await asyncio.sleep(1)
        logger.info(f"Progress: {i + 1}/{duration}")

    return {
        "status": "completed",
        "duration": duration,
    }


@broker.task
async def send_email_task(to: str, subject: str, body: str) -> dict[str, Any]:
    """
    Example email sending task.

    Replace with actual email sending logic (e.g., using aiosmtplib, sendgrid, etc.)

    Args:
        to: Recipient email
        subject: Email subject
        body: Email body

    Returns:
        Result dictionary
    """
    logger.info(f"Sending email to {to}: {subject}")

    # TODO: Implement actual email sending
    # Example with aiosmtplib:
    # import aiosmtplib
    # ...

    # Simulate sending
    await asyncio.sleep(0.5)

    return {
        "status": "sent",
        "to": to,
        "subject": subject,
    }
