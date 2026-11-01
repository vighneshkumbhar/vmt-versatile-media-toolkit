"""
ffmpeg_api.py
FFmpeg execution API.
"""
import uuid
from typing import TYPE_CHECKING, List
from extensions.capabilities import Capability

if TYPE_CHECKING:
    from extensions.api.context import VMTContext

class FFmpegContext:
    def __init__(self, ctx: "VMTContext"):
        self._ctx = ctx

    def run(self, input_file: str, output_file: str, args: List[str], description: str = "") -> None:
        self._ctx._check_capability(Capability.FFMPEG_EXECUTE)
        self._ctx._check_capability(Capability.JOBS_ADD)
        
        # We need to construct a Job and add it.
        # This prevents extensions from running subprocesses directly and ensures jobs are queued.
        from core.job import Job, JobStatus # Local import to avoid circular dependency
        
        job = Job(
            id=str(uuid.uuid4()),
            input_file=input_file,
            output_file=output_file,
            ffmpeg_args=args,
            description=description,
            status=JobStatus.PENDING,
            progress=0.0
        )
        self._ctx.jobs.add_job(job)
