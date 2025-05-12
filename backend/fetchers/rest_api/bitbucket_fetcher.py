import time
from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional

from backend.app.config import app_configuration
from backend.fetchers.base_rest_fetcher import BaseRestFetcher
from backend.graphql.enums import LogLevel
from backend.graphql.git_types import FetcherSettingsInput, RepoData, MergeRequestData


@dataclass
class BitbucketFetcher(BaseRestFetcher):
    """
    Fetcher for retrieving repository data from Bitbucket's REST API using OAuth2.
    """

    base_url: str = app_configuration.BITBUCKET_BASE_URL
    token_url: str = app_configuration.BITBUCKET_TOKEN_URL
    client_id: str = app_configuration.BITBUCKET_CLIENT_ID
    client_secret: str = app_configuration.BITBUCKET_SECRET
    access_token: Optional[str] = None

    FIELD_MAPPING = {
        "name": "name",
        "fullName": "full_name",
        "description": "description",
        "createdAt": "created_on",
        "updatedAt": "updated_on",
        "languages": "language",
    }

    MERGE_REQUESTS_FIELD_MAPPING = {
        "authorName": "author.display_name",
        "description": "summary.raw",
        "createdAt": "created_on",
        "title": "title",
    }

    # ===========================
    # Public Methods
    # ===========================

    async def fetch_projects(
        self,
        settings: FetcherSettingsInput,
        fields: List[str],
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> List[RepoData]:
        """Fetch repositories from Bitbucket and parse them into RepoData."""
        await self._ensure_authenticated(job_logger)
        url = self._build_repositories_url(settings)
        self._log(
            LogLevel.INFO, f"Fetching repositories from Bitbucket: {url}", job_logger
        )

        start_time = time.time()
        data = await self._get(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            job_logger=job_logger,
        )

        repositories = self._extract_values_list(data, job_logger)
        repositories = repositories[: settings.repoCount]

        parsed_data = await self._process_tasks_concurrently(
            [self._parse_repository(repo, fields, job_logger) for repo in repositories],
            "Processing",
            job_logger,
        )
        duration = time.time() - start_time

        self._log(
            LogLevel.INFO,
            f"Fetched and parsed {len(parsed_data)} repositories in {duration:.2f} seconds.",
            job_logger,
        )
        return parsed_data

    async def execute_raw_query(
        self, query: str, job_logger: Optional[Callable[[str], None]] = None
    ) -> None:
        """Not supported for REST-APIs."""
        raise NotImplementedError("Raw GraphQL queries not supported for Bitbucket.")

    # ===========================
    # Private Methods
    # ===========================

    async def _ensure_authenticated(
        self, job_logger: Optional[Callable[[str], None]]
    ) -> None:
        """Authenticate if no access token is present."""
        if not self.access_token:
            self.access_token = await super()._authenticate(
                self.token_url, self.client_id, self.client_secret, job_logger
            )
            if not self.access_token:
                self._log(
                    LogLevel.ERROR,
                    "Authentication failed: No access token received.",
                    job_logger,
                )
                raise RuntimeError("Authentication failed: No access token received.")

    def _build_repositories_url(self, settings: FetcherSettingsInput) -> str:
        """Build the URL for fetching repositories with query parameters."""
        filters = {
            "name~": f'"{settings.searchTerm}"' if settings.searchTerm else None,
            "language~": f'"{settings.programmingLanguage}"'
            if settings.programmingLanguage
            else None,
        }
        query_params = self._build_query_params(filters)
        return f"{self.base_url}/repositories?role=member&q={query_params}"

    async def _parse_repository(
        self,
        repo: Dict[str, Any],
        fields: List[str],
        job_logger: Optional[Callable[[str], None]],
    ) -> RepoData:
        """Parse a single repository dictionary into RepoData."""
        merge_requests = await self._fetch_merge_requests_if_needed(
            repo, fields, job_logger
        )
        return self.parse_repo_data(
            data=repo,
            fields=fields,
            field_mapping=self.FIELD_MAPPING,
            merge_requests=merge_requests,
        )

    async def _fetch_merge_requests_if_needed(
        self,
        repo: Dict[str, Any],
        fields: List[str],
        job_logger: Optional[Callable[[str], None]],
    ) -> List[MergeRequestData]:
        """Fetch merge requests for a repository if required."""
        if any(field.startswith("mergeRequests") for field in fields):
            url = repo.get("links", {}).get("pullrequests", {}).get("href")
            if url:
                return await self._fetch_merge_requests(url, fields, job_logger)
        return []

    async def _fetch_merge_requests(
        self,
        url: str,
        fields: List[str],
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> List[MergeRequestData]:
        """Fetch and map merge requests for a repository from the given URL."""
        raw_merge_requests = await super()._fetch_merge_requests(
            url, self.access_token, job_logger
        )
        return self.parse_merge_requests(
            data=raw_merge_requests,
            fields=fields,
            field_mapping=self.MERGE_REQUESTS_FIELD_MAPPING,
        )
