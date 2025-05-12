import asyncio
import time
from typing import Optional, List, Dict, Any, Callable, TypedDict

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from backend.app.config import app_configuration
from backend.fetchers.base_fetcher import BaseFetcher
from backend.graphql.enums import LogLevel


class PaginatedResponse(TypedDict):
    """TypedDict for paginated API responses."""

    values: List[Dict[str, Any]]
    next: Optional[str]


class BaseRestFetcher(BaseFetcher):
    """
    REST API fetcher with pagination, rate limit handling,
    and protocol-aware error recovery.
    """

    DEFAULT_TIMEOUT: float = app_configuration.DEFAULT_TIMEOUT
    DEFAULT_RETRY_ATTEMPTS: int = app_configuration.MAX_RETRIES
    RETRY_WAIT_MULTIPLIER: float = app_configuration.BACKOFF_FACTOR
    BACKOFF_MIN: float = app_configuration.BACKOFF_MIN
    BACKOFF_MAX: float = app_configuration.BACKOFF_MAX

    @retry(
        stop=stop_after_attempt(DEFAULT_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_WAIT_MULTIPLIER, min=BACKOFF_MIN, max=BACKOFF_MAX
        ),
        retry=retry_if_exception(BaseFetcher._is_retryable_error),
        reraise=True,
    )
    async def _get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Sends a GET request and returns the JSON response.
        """
        self._log(LogLevel.DEBUG, f"Sending GET request to {url}", job_logger)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, headers=headers, params=params, timeout=self.DEFAULT_TIMEOUT
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                self._log(
                    LogLevel.ERROR,
                    f"HTTP error occurred: {e.response.status_code} - {e.response.text}",
                    job_logger,
                )
                raise
            except httpx.RequestError as e:
                self._log(
                    LogLevel.ERROR, f"Request error occurred: {str(e)}", job_logger
                )
                raise

    @retry(
        stop=stop_after_attempt(DEFAULT_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_WAIT_MULTIPLIER, min=BACKOFF_MIN, max=BACKOFF_MAX
        ),
        retry=retry_if_exception(BaseFetcher._is_retryable_error),
        reraise=True,
    )
    async def _post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Sends a POST request and returns the JSON response.
        """
        self._log(LogLevel.DEBUG, f"Sending POST request to {url}", job_logger)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    data=data,
                    headers=headers,
                    auth=auth,
                    timeout=self.DEFAULT_TIMEOUT,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                self._log(
                    LogLevel.ERROR,
                    f"HTTP error occurred: {e.response.status_code} - {e.response.text}",
                    job_logger,
                )
                raise
            except httpx.RequestError as e:
                self._log(
                    LogLevel.ERROR, f"Request error occurred: {str(e)}", job_logger
                )
                raise

    async def _paginate(
        self,
        client: httpx.AsyncClient,
        initial_url: str,
        params: Dict[str, Any],
        limit: int,
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Handles pagination for REST API requests.
        """
        results = []
        current_url = initial_url
        page = 1

        try:
            while current_url and len(results) < limit:
                self._log(
                    LogLevel.DEBUG, f"Fetching page {page}: {current_url}", job_logger
                )

                response = await self._get_response(
                    client, current_url, params, job_logger
                )
                data = self._validate_response_data(response, job_logger)

                # Process results with limit awareness
                batch = data.get(self.RESULTS_KEY, [])[: limit - len(results)]
                results.extend(batch)

                # Determine next page using multiple strategies
                current_url = self._get_next_url(response, data, job_logger)
                page += 1

                # Respect API rate guidelines
                await self._apply_rate_limits(response.headers)

        except Exception as e:
            self._log(
                LogLevel.EXCEPTION,
                f"Pagination aborted at page {page}: {str(e)}",
                job_logger,
            )
            raise

        return results

    async def _get_response(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> httpx.Response:
        """
        Sends a GET request with retry logic.
        """

        @retry(
            stop=stop_after_attempt(self.DEFAULT_RETRY_ATTEMPTS),
            wait=wait_exponential(
                multiplier=app_configuration.BACKOFF_FACTOR,
                min=app_configuration.BACKOFF_MIN,
                max=app_configuration.BACKOFF_MAX,
            ),
            retry=retry_if_exception(self._is_retryable_error),
            reraise=True,
        )
        async def _request_with_retry():
            response = await client.get(
                url, params=params, headers=headers, timeout=self.DEFAULT_TIMEOUT
            )
            self._check_response_status(response)
            return response

        return await _request_with_retry()

    async def _apply_rate_limits(self, headers: Dict) -> None:
        """
        Handles rate limiting based on API headers.
        """
        remaining = headers.get("X-RateLimit-Remaining")
        reset_time = headers.get("X-RateLimit-Reset")

        if remaining == "0" and reset_time:
            try:
                wait = float(reset_time) - time.time()
                if wait > 0:
                    self._log(
                        LogLevel.WARNING,
                        f"Rate limit reached. Waiting for {wait:.2f} seconds.",
                    )
                    await asyncio.sleep(wait)
            except ValueError:
                self._log(LogLevel.ERROR, "Invalid rate limit reset time received.")

    async def _authenticate(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Authenticates with an OAuth2 endpoint to retrieve an access token.
        """
        self._log(LogLevel.INFO, "Authenticating with OAuth2...", job_logger)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                timeout=self.DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get("access_token")
            if access_token:
                self._log(LogLevel.INFO, "Successfully authenticated.", job_logger)
            else:
                self._log(
                    LogLevel.ERROR,
                    "Authentication failed: No access token received.",
                    job_logger,
                )
            return access_token

    def _build_query_params(self, filters: Dict[str, Any]) -> str:
        """
        Builds query parameters for a REST API request based on a dictionary of filters.
        Ensures proper formatting without over-encoding special characters like quotes.
        """
        query_parts = [
            f"{key}{value}" for key, value in filters.items() if value is not None
        ]
        return "&".join(query_parts)

    async def _fetch_merge_requests(
        self,
        url: str,
        access_token: str,
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetches raw merge requests for a repository from the given URL.
        """
        self._log(LogLevel.DEBUG, f"Fetching merge requests from: {url}", job_logger)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=app_configuration.DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

        return data.get("values", [])

    def _extract_values_list(
        self, data: Dict[str, Any], job_logger: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extracts a list of items from a REST API response with a values key.
        """
        if "values" not in data:
            self._log(
                LogLevel.ERROR, f"Unexpected response structure: {data}", job_logger
            )
            raise ValueError(
                "The API response does not contain the expected 'values' key."
            )
        return data["values"]

    async def _process_tasks_concurrently(
        self,
        tasks: List[asyncio.Task],
        stage: str,
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> List[Any]:
        """
        Processes tasks concurrently and logs progress in 10%-steps.
        """
        results = []
        total = len(tasks)
        processed = 0
        last_logged_percent = {"value": -1}

        if total == 0:
            return results

        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            processed += 1
            self._log_progress(processed, total, stage, job_logger, last_logged_percent)

        self._log(
            LogLevel.INFO,
            f"Successfully processed {len(results)} items.",
            job_logger,
        )
        return results
