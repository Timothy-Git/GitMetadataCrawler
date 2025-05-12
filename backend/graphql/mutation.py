import asyncio
from datetime import datetime
from typing import List, Optional, Annotated

import strawberry

from backend.database.jobs import create_job, delete_job, update_job
from backend.graphql.enums import StateEnum, FetchJobMode, PlatformEnum
from backend.graphql.git_types import (
    FetchJob,
    FetcherSettingsInput,
    UpdateFetchJobInput,
    RequestedFieldInput,
    PluginResult,
)
from backend.utils.csv_exporter import CSVExporter
from backend.utils.mutation_utils import (
    process_requested_fields,
    update_job_fields,
    fetch_and_validate_job,
    finalize_job,
    process_fetch_job_based_on_mode,
    intern_job_log,
)
from backend.utils.plugin_enum import PluginEnum
from backend.utils.plugin_registry import PluginRegistry

running_tasks = {}


@strawberry.type(description="Root mutation for executing operations.")
class Mutation:
    @strawberry.mutation(description="Create and save a new fetch job.")
    def create_fetch_job(
        self,
        name: Annotated[
            str, strawberry.argument(description="The name of the fetch job.")
        ],
        mode: Annotated[
            FetchJobMode,
            strawberry.argument(
                description="The mode in which the fetch job is executed."
            ),
        ],
        platform: Annotated[
            PlatformEnum,
            strawberry.argument(
                description="The platform for which the fetch job is created."
            ),
        ],
        fetcher_settings: Annotated[
            Optional[FetcherSettingsInput],
            strawberry.argument(
                description="Settings for the fetcher. Required in ASSISTANT mode."
            ),
        ] = None,
        requested_fields: Annotated[
            Optional[List[RequestedFieldInput]],
            strawberry.argument(
                description="Fields to request from the fetcher. Required in ASSISTANT mode."
            ),
        ] = None,
        raw_query: Annotated[
            Optional[str],
            strawberry.argument(description="Raw query string for EXPERT mode."),
        ] = None,
    ) -> FetchJob:
        if mode == FetchJobMode.ASSISTANT:
            if not fetcher_settings or not requested_fields:
                raise ValueError(
                    "Assistant mode requires fetcher settings and requested fields"
                )
            requested_fields = process_requested_fields(requested_fields)
        elif mode == FetchJobMode.EXPERT and not raw_query:
            raise ValueError("Expert mode requires a raw query")

        job = FetchJob(
            jobId="",  # Set by create_job
            name=name,
            mode=mode,
            platform=platform,
            state=StateEnum.CREATED,
            startTime=None,
            settings=fetcher_settings,
            requestedFields=requested_fields
            if mode == FetchJobMode.ASSISTANT
            else None,
            rawQuery=raw_query if mode == FetchJobMode.EXPERT else None,
            repoData=[],
            log=[],
        )
        job.jobId = create_job(job)
        intern_job_log(job, "Job created")
        return job

    @strawberry.mutation(description="Start asynchronous processing of a fetch job.")
    async def start_fetch_job(
        self,
        job_id: Annotated[
            str, strawberry.argument(description="The ID of the fetch job to start.")
        ],
    ) -> FetchJob:
        job = fetch_and_validate_job(job_id, disallowed_state=StateEnum.SUCCESSFUL)
        if job.state in {StateEnum.FAILURE, StateEnum.STOPPED}:
            intern_job_log(job, "Job resumed")
        job.state = StateEnum.RUNNING
        job.startTime = datetime.now()
        update_job(job)
        intern_job_log(job, "Execution started")
        task = asyncio.create_task(process_fetch_job_based_on_mode(job))
        running_tasks[job_id] = task
        return job

    @strawberry.mutation(description="Stop execution and mark job as stopped.")
    async def stop_fetch_job(
        self,
        job_id: Annotated[
            str, strawberry.argument(description="The ID of the fetch job to stop.")
        ],
    ) -> FetchJob:
        job = fetch_and_validate_job(job_id, allowed_state=StateEnum.RUNNING)
        task = running_tasks.pop(job_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        job.state = StateEnum.STOPPED
        finalize_job(job, StateEnum.STOPPED, "Job was stopped by the user")
        intern_job_log(job, "Execution stopped")
        return job

    @strawberry.mutation(
        description="Remove job (only if the job not currently running)."
    )
    def delete_fetch_job(
        self,
        job_id: Annotated[
            str, strawberry.argument(description="The ID of the fetch job to delete.")
        ],
    ) -> bool:
        fetch_and_validate_job(job_id, disallowed_state=StateEnum.RUNNING)
        return delete_job(job_id)

    @strawberry.mutation(description="Update existing job with new values.")
    def update_fetch_job(
        self,
        job_input: Annotated[
            UpdateFetchJobInput,
            strawberry.argument(description="The updated job input object."),
        ],
    ) -> FetchJob:
        job = fetch_and_validate_job(
            job_input.jobId, disallowed_state=StateEnum.RUNNING
        )
        if job.state == StateEnum.SUCCESSFUL:
            raise ValueError("Cannot modify completed jobs")
        job = update_job_fields(job, job_input)
        job.state = StateEnum.CREATED
        update_job(job)
        intern_job_log(job, "Configuration updated and reset")
        return job

    @strawberry.mutation(
        description="Export the CSV for a job. Returns a file URL (server) or local file path."
    )
    def export_csv(
        self,
        job_id: Annotated[
            str, strawberry.argument(description="The ID of the fetch job to export.")
        ],
        local_export: Annotated[
            bool,
            strawberry.argument(
                description="If true, saves in export path (see .env) and returns the local file path. Otherwise, returns a hosted file URL."
            ),
        ] = False,
    ) -> str:
        job = fetch_and_validate_job(job_id, allowed_state=StateEnum.SUCCESSFUL)
        if not job.repoData:
            raise ValueError("No repository data available for this job.")
        return CSVExporter.export_repo_data_to_csv(
            job.repoData, job_id, local_export=local_export
        )

    @strawberry.mutation(
        description="Execute a plugin for a specific job and export plugin results as CSV."
    )
    def execute_plugin(
        self,
        job_id: Annotated[
            str,
            strawberry.argument(
                description="The ID of the fetch job for plugin execution."
            ),
        ],
        plugin: Annotated[
            PluginEnum, strawberry.argument(description="The plugin to execute.")  # type: ignore
        ],
        local_export: Annotated[
            bool,
            strawberry.argument(
                description="If true, saves plugin CSVs in export path (see .env) and returns local file paths. Otherwise, returns hosted URLs."
            ),
        ] = False,
    ) -> PluginResult:
        job = fetch_and_validate_job(job_id, allowed_state=StateEnum.SUCCESSFUL)
        try:
            plugin_func = PluginRegistry.get(plugin.value)
            result = plugin_func(job, local_export=local_export)
            intern_job_log(job, f"Plugin '{plugin.value}' executed successfully.")
            return result
        except Exception as e:
            intern_job_log(job, f"Plugin '{plugin.value}' execution failed: {e}")
            raise RuntimeError(f"Plugin execution failed: {e}")
