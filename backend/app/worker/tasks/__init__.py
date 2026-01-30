"""Background tasks."""

from app.worker.tasks.taskiq_examples import example_task as taskiq_example_task
from app.worker.tasks.taskiq_examples import long_running_task as taskiq_long_running_task

__all__ = [
    "taskiq_example_task",
    "taskiq_long_running_task",
]
