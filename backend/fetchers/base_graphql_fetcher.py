import abc
import asyncio
import re
import textwrap
import time
from typing import Optional, Dict, Any, List, Callable, Set

from tenacity import stop_after_attempt, wait_exponential, retry_if_exception, retry

from backend.app.config import app_configuration
from backend.fetchers.base_fetcher import BaseFetcher
from backend.graphql.enums import LogLevel
from backend.graphql.git_types import FetcherSettingsInput, RepoData
from backend.utils.token_pool import TokenPool


class BaseGraphQLFetcher(BaseFetcher, abc.ABC):
    """
    Abstract base class for GraphQL-based fetchers.
    Handles HTTP requests, token rotation, retry logic, and query formatting.
    """

    DEFAULT_TIMEOUT: float = app_configuration.DEFAULT_TIMEOUT
    DEFAULT_RETRY_ATTEMPTS: int = app_configuration.MAX_RETRIES
    RETRY_WAIT_MULTIPLIER: float = app_configuration.BACKOFF_FACTOR
    BACKOFF_MIN: float = app_configuration.BACKOFF_MIN
    BACKOFF_MAX: float = app_configuration.BACKOFF_MAX

    def __init__(self, token_pool: TokenPool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_pool = token_pool

    async def close(self) -> None:
        """Closes the persistent HTTP client."""
        await self.client.aclose()

    @abc.abstractmethod
    def build_query(
        self, fetch_settings: FetcherSettingsInput, fields: List[str]
    ) -> str:
        """Build the GraphQL query based on provided settings and fields."""
        pass

    async def _make_request(
        self,
        base_url: str,
        query: str,
        extra_headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Sends a request to the GraphQL API with the specified query and headers.
        Rotates tokens on failure and handles rate limits and cooldowns.
        """

        async def make_request(token: str):
            @retry(
                stop=stop_after_attempt(self.DEFAULT_RETRY_ATTEMPTS),
                wait=wait_exponential(
                    multiplier=self.RETRY_WAIT_MULTIPLIER,
                    min=self.BACKOFF_MIN,
                    max=self.BACKOFF_MAX,
                ),
                retry=retry_if_exception(self._is_retryable_error),
                reraise=True,
            )
            async def _request_with_retry():
                # Prepare headers
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }
                if extra_headers:
                    headers.update(extra_headers)

                # Send request and log duration
                start_time = time.time()
                response = await self.client.post(
                    base_url,
                    json={"query": query},
                    headers=headers,
                    timeout=timeout or self.DEFAULT_TIMEOUT,
                )
                duration = time.time() - start_time
                self._log(
                    LogLevel.DEBUG,
                    f"Request to {base_url} completed in {duration:.2f}s",
                    job_logger,
                )

                # Check response and handle errors
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    error_details = "\n".join([str(err) for err in data["errors"]])
                    self._log(
                        LogLevel.ERROR,
                        f"GraphQL API returned errors:\n{error_details}",
                        job_logger,
                    )
                    raise RuntimeError(error_details)
                return data

            return await _request_with_retry()

        # Token rotation and retry logic
        return await self._request_with_token_rotation(
            self.token_pool,
            make_request,
            job_logger=job_logger,
            ban_on_errors=["rate limit", "authentication", "unauthorized"],
        )

    @staticmethod
    def format_graphql_query(query: str) -> str:
        """
        Formats a GraphQL query by removing unnecessary indentation and adding line breaks for readability.
        """
        # Clean up and format the query string
        query = textwrap.dedent(query).strip()
        query = re.sub(r"\{", "{\n", query)
        query = re.sub(r"\}", "\n}\n", query)
        query = re.sub(r"\n+", "\n", query)

        indentation_level = 0
        formatted_lines = []

        for line in query.splitlines():
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if stripped_line.startswith("}"):
                indentation_level = max(indentation_level - 1, 0)
            formatted_lines.append("    " * indentation_level + stripped_line)
            if stripped_line.endswith("{"):
                indentation_level += 1

        return "\n".join(formatted_lines)

    def _map_fields(self, fields: List[str], mapping: Dict[str, str]) -> List[str]:
        """Map fields using the provided mapping dictionary."""
        mapped_fields = []
        for field_name in fields:
            if field_name in mapping:
                mapped_field = mapping[field_name]
                if "." in mapped_field:
                    top_level, nested = mapped_field.split(".", 1)
                    mapped_fields.append(f"{top_level} {{ {nested} }}")
                else:
                    mapped_fields.append(mapped_field)
        return mapped_fields

    def _build_merge_requests_query(
        self,
        subfields: List[str],
        max_mrs: int,
        field_mapping: Dict[str, str],
        mr_node_name: str = "mergeRequests",
    ) -> str:
        """Build the merge requests part of the query."""
        merge_requests_fields = self._map_fields(subfields, field_mapping)
        fields_str = " ".join(merge_requests_fields)
        query = f"""
        {mr_node_name}(first: {max_mrs}) {{
            nodes {{
                {fields_str}
            }}
        }}
        """
        return textwrap.dedent(query).strip()

    def _parse_single_node(
        self,
        node: Dict[str, Any],
        fields: Set[str],
        repo_field_mapping: Dict[str, str],
        mr_field_mapping: Dict[str, str],
        mr_node_name: str = "mergeRequests",
    ) -> Optional[RepoData]:
        """Parse a single repository/project node."""
        merge_requests = None
        if any(field.startswith("mergeRequests.") for field in fields):
            merge_requests_data = node.get(mr_node_name, {}).get("nodes", [])
            merge_requests = self.parse_merge_requests(
                data=merge_requests_data,
                fields=fields,
                field_mapping=mr_field_mapping,
            )
        return self.parse_repo_data(
            data=node,
            fields=fields,
            field_mapping=repo_field_mapping,
            merge_requests=merge_requests,
        )

    async def _parse_nodes_concurrently(
        self,
        nodes: List[Dict[str, Any]],
        fields: List[str],
        settings: FetcherSettingsInput,
        repo_field_mapping: Dict[str, str],
        mr_field_mapping: Dict[str, str],
        mr_node_name: str = "mergeRequests",
        job_logger: Optional[Callable[[str], None]] = None,
        executor=None,
    ) -> List[RepoData]:
        """Parse nodes concurrently using threads or executors."""
        parsed_data: List[RepoData] = []
        fields_set: Set[str] = set(fields)
        valid_nodes = [node for node in nodes if isinstance(node, dict)]

        if not valid_nodes:
            self._log(LogLevel.WARNING, "No valid nodes to parse.", job_logger)
            return parsed_data

        batch_size = max(
            5, min(20, len(valid_nodes) // max(1, (settings.repoCount // 10)))
        )
        self._log(
            LogLevel.DEBUG,
            f"Processing {len(valid_nodes)} nodes in batches of {batch_size}.",
            job_logger,
        )

        total_nodes = len(valid_nodes)
        processed_count = 0
        loop = asyncio.get_running_loop()
        last_logged_percent = {"value": -1}

        for i in range(0, total_nodes, batch_size):
            batch = valid_nodes[i : i + batch_size]
            self._log(
                LogLevel.DEBUG,
                f"Processing batch {i // batch_size + 1} with {len(batch)} nodes.",
                job_logger,
            )
            if executor:
                tasks = [
                    loop.run_in_executor(
                        executor,
                        self._parse_single_node,
                        node,
                        fields_set,
                        repo_field_mapping,
                        mr_field_mapping,
                        mr_node_name,
                    )
                    for node in batch
                ]
            else:
                tasks = [
                    asyncio.to_thread(
                        self._parse_single_node,
                        node,
                        fields_set,
                        repo_field_mapping,
                        mr_field_mapping,
                        mr_node_name,
                    )
                    for node in batch
                ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    self._log(
                        LogLevel.ERROR,
                        f"Error parsing node: {result}. Node data: {batch[idx]}",
                        job_logger,
                    )
                elif result is not None:
                    parsed_data.append(result)
            processed_count += len(batch)
            self._log_progress(
                processed_count,
                total_nodes,
                "Processing",
                job_logger,
                last_logged_percent,
            )

        self._log(
            LogLevel.INFO, f"Successfully parsed {len(parsed_data)} nodes.", job_logger
        )
        return parsed_data
