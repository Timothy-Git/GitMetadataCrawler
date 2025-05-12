from typing import Annotated, List, Optional

import strawberry

from backend.database.jobs import get_all_jobs, get_job
from backend.fetchers.fetcher_factory import FetcherFactory
from backend.graphql.enums import PlatformEnum
from backend.graphql.git_types import FetchJob, FetcherSettingsInput, RepoData
from backend.utils.database_utils import convert_to_dataclass
from backend.utils.logger import logger


@strawberry.type(description="Root query for fetching data.")
class Query:
    @strawberry.field(
        description="[Debug] Fetch projects from a specified platform without creating a job."
    )
    async def fetch_projects(
        self,
        platform: Annotated[
            PlatformEnum,
            strawberry.argument(description="The platform to fetch projects from."),
        ],
        settings: Annotated[
            FetcherSettingsInput,
            strawberry.argument(
                description="Settings to configure the fetch operation."
            ),
        ],
        info: strawberry.types.Info,
    ) -> List[RepoData]:
        """Dynamically fetch projects from the specified platform."""
        try:
            requested_fields = (
                [f.name for f in info.selected_fields[0].selections]
                if info.selected_fields and info.selected_fields[0].selections
                else []
            )
        except Exception as e:
            logger.error(f"Field selection error: {e}")
            raise ValueError("Invalid query structure") from e

        if not requested_fields:
            logger.info("No fields selected, using default field selection.")

        logger.debug(f"Requested fields: {requested_fields}")

        fetcher = FetcherFactory.get_fetcher(platform)
        if not fetcher:
            logger.error(f"Unsupported platform: {platform}")
            raise ValueError(f"No fetcher for {platform}")

        try:
            return await fetcher.fetch_projects(settings, requested_fields)
        except Exception as e:
            logger.error(f"Fetch failure: {e}")
            raise RuntimeError(f"Project fetch failed: {e}") from e

    @strawberry.field(
        description="[Debug] Execute a raw GraphQL query directly on the specified platform."
    )
    async def bypass_raw_query(
        self,
        raw_query: Annotated[
            str, strawberry.argument(description="The raw GraphQL query to execute.")
        ],
        platform: Annotated[
            PlatformEnum,
            strawberry.argument(
                description="The platform to execute the query on (only GraphQL platform)."
            ),
        ],
    ) -> strawberry.scalars.JSON:
        """Execute a raw GraphQL query directly on the platform."""
        if not raw_query or not raw_query.strip():
            logger.error("Empty query received")
            raise ValueError("Query cannot be empty")

        fetcher = FetcherFactory.get_fetcher(platform)
        if not fetcher:
            logger.error(f"Unsupported platform: {platform}")
            raise ValueError(f"No fetcher for {platform}")

        try:
            response = await fetcher.execute_raw_query(raw_query)
            logger.info("Raw query executed successfully")
            return response
        except Exception as e:
            logger.error(f"Query failure: {e}\nQuery: {raw_query[:100]}...")
            raise RuntimeError(f"Query execution failed: {e}") from e

    @strawberry.field(description="Retrieve fetch jobs from the database.")
    def get_fetch_jobs(
        self,
        job_id: Annotated[
            Optional[str],
            strawberry.argument(
                description="The ID of the fetch job to retrieve. If not provided, all jobs are retrieved."
            ),
        ] = None,
        includeDebug: Annotated[
            bool,
            strawberry.argument(
                description="Whether to include Debug logs in the results. Defaults to False."
            ),
        ] = False,
    ) -> List[FetchJob]:
        """Retrieve fetch jobs from the database, optionally filtering out DEBUG logs."""
        jobs: List[FetchJob]
        if job_id:
            job = get_job(job_id)
            if not job:
                raise ValueError(f"No job found with the given ID: {job_id}")
            jobs = [job]
        else:
            jobs = get_all_jobs()

        if not includeDebug:  # Filter out DEBUG logs if includeDebug is False
            for job in jobs:
                job.log = [log for log in job.log if " - DEBUG - " not in log]

        # Convert repoData and mergeRequests entries to their respective data classes
        for job in jobs:
            job.repoData = [
                convert_to_dataclass(RepoData, repo) for repo in job.repoData
            ]

        return jobs
