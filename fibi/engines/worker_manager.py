"""Managed worker layer for background Fibi tasks."""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkerTaskStatus:
    task_id: str
    name: str
    group: str
    done: bool
    cancelled: bool
    error: str = ""


class WorkerManager:
    """Small wrapper around ThreadPoolExecutor with task metadata."""

    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="fibi-worker")
        self._tasks: dict[str, tuple[str, str, Future[Any]]] = {}

    def submit_task(
        self,
        name: str,
        fn: Callable[..., Any],
        *args: Any,
        priority: int = 0,
        group: str = "default",
        **kwargs: Any,
    ) -> str:
        task_id = uuid.uuid4().hex

        def run() -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception:
                LOGGER.exception("Worker task failed: %s", name)
                raise

        future = self._executor.submit(run)
        self._tasks[task_id] = (name, group, future)
        LOGGER.info("Worker task submitted: %s priority=%s group=%s", name, priority, group)
        return task_id

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        return bool(task and task[2].cancel())

    def cancel_group(self, group: str) -> int:
        count = 0
        for task_id, (_, task_group, future) in list(self._tasks.items()):
            if task_group == group and future.cancel():
                count += 1
                LOGGER.info("Worker task cancelled: %s", task_id)
        return count

    def status(self, task_id: str) -> WorkerTaskStatus | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        name, group, future = task
        error = ""
        if future.done() and not future.cancelled():
            try:
                future.result()
            except Exception as exc:
                error = str(exc)
        return WorkerTaskStatus(task_id, name, group, future.done(), future.cancelled(), error)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
