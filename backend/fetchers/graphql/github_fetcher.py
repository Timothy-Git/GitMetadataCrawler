import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from time import time
from typing import List, Dict, Any, Optional, Callable

from backend.fetchers.base_graphql_fetcher import BaseGraphQLFetcher
from backend.graphql.enums import LogLevel
from backend.graphql.git_types import FetcherSettingsInput, RepoData
from backend.utils.token_pool import TokenPool


@dataclass
class GitHubFetcher(BaseGraphQLFetcher):
    base_url: str
    token_pool: TokenPool
    executor: ThreadPoolExecutor = field(init=False, default=None)

    # Field mappings for repositories and merge requests
    FIELD_MAPPING = {
        "name": "name",
        "fullName": "nameWithOwner",
        "description": "description",
        "starCount": "stargazerCount",
        "createdAt": "createdAt",
        "updatedAt": "updatedAt",
        "languages": "primaryLanguage.name",
    }

    MERGE_REQUESTS_FIELD_MAPPING = {
        "authorName": "author.login",
        "createdAt": "createdAt",
        "description": "bodyText",
        "title": "title",
    }


    def __post_init__(self):
        """Initialize the base class and set up a ThreadPoolExecutor for I/O-bound tasks."""
        super().__init__(token_pool=self.token_pool)
        max_threads = min(32, (os.cpu_count() or 1) * 2)
        self.executor = ThreadPoolExecutor(max_workers=max_threads)

    # ===========================
    # Public Methods
    # ===========================

    async def fetch_projects(
        self,
        settings: FetcherSettingsInput,
        fields: List[str],
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> List[RepoData]:
        """Fetch and parse repositories from GitHub."""
        self._log(LogLevel.INFO, "Fetching repositories from GitHub...", job_logger)
        start_time = time()

        all_repositories: List[Dict[str, Any]] = []
        cursor = None
        remaining_limit = settings.repoCount
        fetched_count = 0
        max_repos_per_query = 1000  # GitHub API limit for a single query
        iteration_count = 0  # To track the number of iterations

        # Define dynamic sort modes
        sort_modes = [
            "stars-desc",  # Most starred repositories
            "updated-desc",  # Recently updated repositories
            "forks-desc",  # Most forked repositories
            "help-wanted-issues-desc",  # Repositories with the most help-wanted issues
            "best-match",  # Default GitHub sorting
            "stars-asc",  # Least starred repositories
            "updated-asc",  # Least recently updated repositories
            "forks-asc",  # Least forked repositories
        ]

        try:
            # Initial fetch
            query = self.build_query(settings, fields, cursor)
            self._log(
                LogLevel.DEBUG,
                f"GraphQL Query:\n{self.format_graphql_query(query)}",
                job_logger,
            )
            response = await self._make_request(
                self.base_url, query, job_logger=job_logger
            )
            repositories = self._extract_repositories(response)
            if repositories:
                all_repositories.extend(repositories)
                fetched_count += len(repositories)
                remaining_limit -= len(repositories)

            page_info = response["data"]["search"]["pageInfo"]
            cursor = (
                page_info.get("endCursor") if page_info.get("hasNextPage") else None
            )

            # Pagination and sort mode cycling
            while remaining_limit > 0:
                iteration_count += 1
                self._log(
                    LogLevel.DEBUG,
                    f"Starting iteration {iteration_count} for fetching repositories.",
                    job_logger,
                )
                current_limit = min(remaining_limit, max_repos_per_query)

                while current_limit > 0:
                    sort_mode = (
                        sort_modes[iteration_count % len(sort_modes)]
                        if settings.repoCount > max_repos_per_query
                        else "best-match"
                    )
                    query = self.build_query(settings, fields, cursor, sort_mode)
                    self._log(
                        LogLevel.DEBUG,
                        f"GraphQL Query (sort: {sort_mode}):\n{self.format_graphql_query(query)}",
                        job_logger,
                    )
                    response = await self._make_request(
                        self.base_url, query, job_logger=job_logger
                    )
                    repositories = self._extract_repositories(response)

                    if not repositories:
                        self._log(
                            LogLevel.WARNING, "No more repositories found.", job_logger
                        )
                        break

                    all_repositories.extend(repositories)
                    fetched_count += len(repositories)
                    current_limit -= len(repositories)
                    remaining_limit -= len(repositories)
                    self._log_progress(
                        fetched_count, settings.repoCount, "Fetching", job_logger
                    )

                    page_info = response["data"]["search"]["pageInfo"]
                    if not page_info.get("hasNextPage"):
                        break
                    cursor = page_info.get("endCursor")

                if remaining_limit > 0:
                    self._log(
                        LogLevel.INFO,
                        "GitHub API-Limit reached - Switching to the next sort mode to fetch more repositories.",
                        job_logger,
                    )
                    cursor = None

            if not all_repositories:
                self._log(LogLevel.ERROR, "No repositories found.", job_logger)
                raise RuntimeError("No repositories found.")

            all_repositories = all_repositories[: settings.repoCount]
            parsed_data = await self._parse_nodes_concurrently(
                all_repositories,
                fields,
                settings,
                repo_field_mapping=self.FIELD_MAPPING,
                mr_field_mapping=self.MERGE_REQUESTS_FIELD_MAPPING,
                mr_node_name="pullRequests",
                job_logger=job_logger,
                executor=self.executor,
            )
            duration = time() - start_time
            self._log(
                LogLevel.INFO,
                f"Fetched and parsed {len(parsed_data)} repositories in {duration:.2f} seconds.",
                job_logger,
            )
            return parsed_data

        except Exception as e:
            self._log(
                LogLevel.ERROR, f"Error during fetch_projects: {str(e)}", job_logger
            )
            raise RuntimeError(f"Failed to fetch projects: {str(e)}") from e

    async def execute_raw_query(
        self, query: str, job_logger: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Execute a raw GraphQL query on GitHub."""
        if not query.strip():
            self._log(LogLevel.ERROR, "Received an empty raw query.", job_logger)
            raise ValueError("The raw query must not be empty.")

        self._log(LogLevel.INFO, "Executing raw GraphQL query on GitHub...", job_logger)
        start_time = time()

        try:
            response = await self._make_request(
                self.base_url, query, job_logger=job_logger
            )
            if not isinstance(response, dict) or "data" not in response:
                self._log(
                    LogLevel.ERROR,
                    f"Unexpected response format: {response}",
                    job_logger,
                )
                raise ValueError("Invalid response structure from GitHub API.")

            repo_count = len(response["data"].get("search", {}).get("edges", []))
            duration = time() - start_time

            self._log(
                LogLevel.INFO,
                f"Raw query executed successfully. Retrieved {repo_count} repositories in {duration:.2f} seconds.",
                job_logger,
            )
            self._log(LogLevel.DEBUG, f"Raw query response: {response}", job_logger)

            return {
                "response": response,
                "repo_count": repo_count,
                "duration": duration,
            }

        except Exception as e:
            self._log(
                LogLevel.ERROR, f"Error executing raw query: {str(e)}", job_logger
            )
            self._log(LogLevel.DEBUG, f"Failed raw query: {query}", job_logger)
            raise RuntimeError("Failed to execute raw query on GitHub.") from e

    def build_query(
        self,
        settings: FetcherSettingsInput,
        fields: List[str],
        after_cursor: Optional[str] = None,
        sort_mode: str = "stars-desc",
    ) -> str:
        """Build a GraphQL query with pagination and sorting support."""
        normal_fields = [f for f in fields if not f.startswith("mergeRequests.")]
        merge_requests_subfields = [
            f.split(".", 1)[1] for f in fields if f.startswith("mergeRequests.")
        ]

        selected_fields_parts = self._map_fields(normal_fields, self.FIELD_MAPPING)
        if merge_requests_subfields:
            merge_requests_query = self._build_merge_requests_query(
                merge_requests_subfields,
                settings.maxMRs,
                self.MERGE_REQUESTS_FIELD_MAPPING,
                mr_node_name="pullRequests",
            )
            selected_fields_parts.append(merge_requests_query)

        query_filters = self._build_query_filters(settings)
        after_clause = f', after: "{after_cursor}"' if after_cursor else ""
        query = f"""
        {{
            search(query: "{query_filters} sort:{sort_mode}" type: REPOSITORY first: {min(settings.repoCount, 50)}{after_clause}) {{
                edges {{
                    node {{
                        ... on Repository {{
                            {"\n".join(selected_fields_parts)}
                        }}
                    }}
                }}
                pageInfo {{
                    hasNextPage
                    endCursor
                }}
            }}
        }}
        """
        return query

    # ===========================
    # Private Methods
    # ===========================

    def _build_query_filters(self, settings: FetcherSettingsInput) -> str:
        """Build query filters for the GraphQL query."""
        filters = []
        if settings.searchTerm:
            filters.append(settings.searchTerm)
        if settings.programmingLanguage:
            filters.append(f"language:{settings.programmingLanguage}")
        if not filters:
            filters.append("stars:>=0")
        return " ".join(filters)

    def _extract_repositories(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract repository nodes from the GraphQL response."""
        try:
            edges = response["data"]["search"].get("edges", [])
            nodes = [
                edge.get("node") for edge in edges if isinstance(edge.get("node"), dict)
            ]
            for edge in edges:
                if not isinstance(edge.get("node"), dict):
                    self._log(
                        LogLevel.WARNING,
                        f"Skipping invalid repository node: {edge.get('node')}",
                        None,
                    )
            return nodes
        except (KeyError, TypeError):
            self._log(LogLevel.ERROR, f"Invalid response structure: {response}", None)
            raise ValueError("Invalid response structure.")
