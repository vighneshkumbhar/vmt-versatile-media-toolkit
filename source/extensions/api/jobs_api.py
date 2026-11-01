"""
jobs_api.py
Jobs API for extensions.
"""
from typing import TYPE_CHECKING, List, Any
from extensions.capabilities import Capability

if TYPE_CHECKING:
    from extensions.api.context import VMTContext

class JobsContext:
    def __init__(self, ctx: "VMTContext"):
        self._ctx = ctx

    def add_job(self, job: Any) -> None:
        self._ctx._check_capability(Capability.JOBS_ADD)
        if hasattr(self._ctx._main_window, "job_queue"):
            self._ctx._main_window.job_queue.add_job(job)

    def list_jobs(self) -> List[Any]:
        self._ctx._check_capability(Capability.JOBS_READ)
        if hasattr(self._ctx._main_window, "job_queue"):
            return self._ctx._main_window.job_queue.get_all_jobs()
        return []
