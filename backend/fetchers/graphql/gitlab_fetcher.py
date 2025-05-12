from dataclasses import dataclass, field
from textwrap import dedent
from time import time
from typing import List, Dict, Any, Optional, Callable

from backend.fetchers.base_graphql_fetcher import BaseGraphQLFetcher
from backend.graphql.enums import LogLevel
from backend.graphql.git_types import RepoData, FetcherSettingsInput
from backend.utils.token_pool import TokenPool


@dataclass
class GitLabFetcher(BaseGraphQLFetcher):
    base_url: str
    token_pool: TokenPool = field(repr=False)

    # Field mappings for repositories and merge requests
    FIELD_MAPPING = {
        "name": "name",
        "fullName": "fullPath",
        "description": "description",
        "starCount": "starCount",
        "createdAt": "createdAt",
        "updatedAt": "updatedAt",
        "languages": "languages.name",
    }

    MERGE_REQUESTS_FIELD_MAPPING = {
        "authorName": "author.name",
        "createdAt": "createdAt",
        "description": "description",
        "title": "title",
    }

    def __post_init__(self):
        """Ensure the base class is initialized to set up the persistent HTTP client."""
        super().__init__(token_pool=self.token_pool)

    # ================================================================
    # Public Methods
    # ================================================================

    async def fetch_projects(
        self,
        settings: FetcherSettingsInput,
        fields: List[str],
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> List[RepoData]:
        """Fetch and parse repositories from GitLab."""
        self._log(LogLevel.INFO, "Fetching repositories from GitLab...", job_logger)
        start_time = time()

        all_projects: List[Dict[str, Any]] = []
        cursor = None
        remaining_limit = settings.repoCount

        try:
            while remaining_limit > 0:
                query = self.build_query(settings, fields, cursor)
                self._log(
                    LogLevel.DEBUG,
                    f"GraphQL Query:\n{self.format_graphql_query(query)}",
                    job_logger,
                )
                response = await self._make_request(
                    self.base_url, query, job_logger=job_logger
                )
                projects = self._extract_projects(response)

                if not projects:
                    self._log(
                        LogLevel.WARNING, "No more repositories found.", job_logger
                    )
                    break

                all_projects.extend(projects)
                remaining_limit -= len(projects)
                self._log_progress(
                    len(all_projects), settings.repoCount, "Fetching", job_logger
                )

                page_info = response["data"]["projects"]["pageInfo"]
                if not page_info.get("hasNextPage"):
                    break
                cursor = page_info.get("endCursor")

            if not all_projects:
                raise RuntimeError("No repositories found.")

            all_projects = all_projects[: settings.repoCount]
            parsed_data = await self._parse_nodes_concurrently(
                all_projects,
                fields,
                settings,
                repo_field_mapping=self.FIELD_MAPPING,
                mr_field_mapping=self.MERGE_REQUESTS_FIELD_MAPPING,
                mr_node_name="mergeRequests",
                job_logger=job_logger,
            )
            duration = time() - start_time
            self._log(
                LogLevel.INFO,
                f"Fetched and parsed {len(parsed_data)} repositories in {duration:.2f} seconds.",
                job_logger,
            )
            return parsed_data

        except Exception as e:
            self._log(LogLevel.ERROR, f"Failed to fetch repositories: {e}", job_logger)
            raise RuntimeError(f"Failed to fetch repositories: {e}") from e

    async def execute_raw_query(
        self, query: str, job_logger: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Execute a raw GraphQL query on GitLab."""
        if not query.strip():
            self._log(LogLevel.ERROR, "Received an empty raw query.", job_logger)
            raise ValueError("The raw query must not be empty.")

        self._log(LogLevel.INFO, "Executing raw GraphQL query on GitLab...", job_logger)
        start_time = time()

        try:
            response = await self._make_request(
                self.base_url, query, job_logger=job_logger
            )
            repo_nodes = response.get("data", {}).get("projects", {}).get("nodes", [])
            repo_count = len(repo_nodes) if isinstance(repo_nodes, list) else 0
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
                LogLevel.ERROR, f"Error executing raw query on GitLab: {e}", job_logger
            )
            raise RuntimeError("Failed to execute raw query on GitLab.") from e

    def build_query(
        self,
        settings: FetcherSettingsInput,
        fields: List[str],
        cursor: Optional[str] = None,
    ) -> str:
        """Build the GraphQL query dynamically based on client-requested fields and settings."""
        normal_fields = [
            field for field in fields if not field.startswith("mergeRequests.")
        ]
        merge_requests_subfields = [
            field.split(".", 1)[1]
            for field in fields
            if field.startswith("mergeRequests.")
        ]

        selected_fields_parts = self._map_fields(normal_fields, self.FIELD_MAPPING)
        if merge_requests_subfields:
            merge_requests_query = self._build_merge_requests_query(
                merge_requests_subfields,
                settings.maxMRs,
                self.MERGE_REQUESTS_FIELD_MAPPING,
                mr_node_name="mergeRequests",
            )
            selected_fields_parts.append(merge_requests_query)

        query_filters = self._build_query_filters(settings)
        after_clause = f', after: "{cursor}"' if cursor else ""
        query = dedent(f"""
            {{
                projects(first: {settings.repoCount}{after_clause}{"," if query_filters else ""} {query_filters}) {{
                    nodes {{
                        {"\n".join(selected_fields_parts)}
                    }}
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                }}
            }}
        """).strip()
        return query

    # ================================================================
    # Private Methods
    # ================================================================

    def _extract_projects(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract project nodes from the GraphQL response."""
        try:
            nodes = response["data"]["projects"].get("nodes", [])
            if not isinstance(nodes, list):
                raise ValueError("Expected 'nodes' to be a list.")
            return nodes
        except (KeyError, TypeError) as e:
            self._log(LogLevel.ERROR, f"Invalid response structure: {e}", None)
            raise ValueError("Invalid response structure.")

    def _build_query_filters(self, settings: FetcherSettingsInput) -> str:
        """Build query filters dynamically based on settings input."""
        filters = [
            f'search: "{settings.searchTerm}"' if settings.searchTerm else None,
            f'programmingLanguageName: "{settings.programmingLanguage}"'
            if settings.programmingLanguage
            else None,
        ]
        return ", ".join(filter(None, filters))
