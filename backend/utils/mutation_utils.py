import logging
from datetime import datetime
from typing import Optional, List

from backend.database.jobs import update_job, get_job
from backend.fetchers.fetcher_factory import FetcherFactory
from backend.graphql.enums import StateEnum, FetchJobMode
from backend.graphql.git_types import FetchJob, FetcherSettings, RequestedFieldInput

logger = logging.getLogger(__name__)


class JobException(Exception):
    """Custom exception for job processing errors."""
    pass


def _log_to_job(job: FetchJob, message: str) -> None:
    """Append a log entry to the job log and persist it."""
    job.log.append(message)
    update_job(job)


def append_job_log(job: FetchJob, message: str) -> None:
    """
    Append a log entry to the job log without timestamp or level.
    Used for messages that are already formatted (e.g. from fetchers).
    """
    _log_to_job(job, message)


def intern_job_log(job: FetchJob, message: str, level: str = "INFO") -> None:
    """
    Append a log entry with timestamp and level to the job log.
    Used for internal logging.
    """
    timestamp = datetime.now().isoformat()
    formatted_log = f"{timestamp} - {level.upper()} - {message}"
    _log_to_job(job, formatted_log)


def validate_job_state(
    job: FetchJob,
    allowed_state: Optional[StateEnum],
    disallowed_state: Optional[StateEnum],
) -> None:
    """Validate the state of a job."""
    if allowed_state and job.state != allowed_state:
        raise JobException(f"Invalid state: {job.state}, required {allowed_state}")
    if disallowed_state and job.state == disallowed_state:
        raise JobException(f"Job in forbidden state: {disallowed_state}")


def fetch_and_validate_job(
    job_id: str,
    allowed_state: Optional[StateEnum] = None,
    disallowed_state: Optional[StateEnum] = None,
) -> FetchJob:
    """Fetch a job by ID and validate its state."""
    job = get_job(job_id)
    if not job:
        raise JobException(f"Job {job_id} not found")
    validate_job_state(job, allowed_state, disallowed_state)
    intern_job_log(job, "Validation passed")
    return job


def finalize_job(
    job: FetchJob, state: StateEnum, message: str, repo_data: Optional[List] = None
) -> None:
    """Finalize a job with a given state and optional repository data."""
    if not job.startTime:
        raise JobException("Cannot finalize unstarted job")
    job.state = state
    job.endTime = datetime.now()
    job.executionTime = (job.endTime - job.startTime).total_seconds()
    if repo_data is not None:
        job.repoData = repo_data
        message += f" with {len(repo_data)} repositories"
    intern_job_log(job, f"{message} ({job.executionTime}s)")
    update_job(job)


async def process_fetch_job_based_on_mode(job: FetchJob) -> None:
    """
    Execute job processing according to the specified mode (ASSISTANT or EXPERT).
    Handles logging and error management.
    """
    try:
        fetcher = FetcherFactory.get_fetcher(job.platform)
        if not fetcher:
            raise JobException(f"Unsupported platform: {job.platform}")

        def job_logger(msg: str) -> None:
            append_job_log(job, msg)

        intern_job_log(job, f"Starting {job.mode.value} mode processing")

        if job.mode == FetchJobMode.ASSISTANT:
            repo_data = await fetcher.fetch_projects(
                job.settings, job.requestedFields, job_logger=job_logger
            )
        elif job.mode == FetchJobMode.EXPERT:
            repo_data = await fetcher.execute_raw_query(
                job.rawQuery, job_logger=job_logger
            )
        else:
            raise ValueError(f"Invalid mode: {job.mode}")

        finalize_job(job, StateEnum.SUCCESSFUL, "Completed", repo_data)
    except Exception as e:
        job.state = StateEnum.FAILURE
        intern_job_log(job, f"Processing error: {e}")
        finalize_job(job, StateEnum.FAILURE, "Failed")
        logger.error(f"Job failure: {e}", exc_info=True)
        raise RuntimeError(f"Processing failure: {e}") from e


def process_requested_fields(requested_fields: List[RequestedFieldInput]) -> List[str]:
    """
    Convert requested fields (with subfields) into a flat list of field strings.
    """
    processed_fields = []
    for field in requested_fields:
        if field.field == "mergeRequests":
            subs = field.subfields or [
                "authorName",
                "createdAt",
                "description",
                "title",
            ]
            processed_fields.extend(f"mergeRequests.{sub}" for sub in subs)
        else:
            processed_fields.append(field.field)
    return processed_fields


def update_job_fields(job, job_input):
    """
    Update job fields from an input object.
    """
    update_map = {
        "name": job_input.name,
        "mode": job_input.mode,
        "platform": job_input.platform,
        "settings": FetcherSettings(**job_input.fetcherSettings.__dict__)
        if getattr(job_input, "fetcherSettings", None)
        else None,
        "requestedFields": getattr(job_input, "requestedFields", None),
        "rawQuery": getattr(job_input, "rawQuery", None),
    }
    for attr, value in update_map.items():
        if value is not None:
            setattr(job, attr, value)
    return job
