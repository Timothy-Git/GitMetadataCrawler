import abc
import asyncio
from datetime import datetime
from http import HTTPStatus
from typing import Optional, Any, Dict, Callable, List

import httpx
from httpx import RequestError, HTTPStatusError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from backend.app.config import app_configuration
from backend.graphql.enums import DataType, LogLevel
from backend.graphql.git_types import MergeRequestData, RepoData
from backend.utils.token_pool import TokenPool


class BaseFetcher(abc.ABC):
    """
    Base class with shared functionality for different fetcher implementations.
    Handles retry logic, error checking, and common data processing methods.
    """

    DEFAULT_RETRY_ATTEMPTS: int = app_configuration.MAX_RETRIES
    DEFAULT_TIMEOUT: float = app_configuration.DEFAULT_TIMEOUT
    RETRY_WAIT_MULTIPLIER: float = app_configuration.BACKOFF_FACTOR
    BACKOFF_MIN: float = app_configuration.BACKOFF_MIN
    BACKOFF_MAX: float = app_configuration.BACKOFF_MAX
    REQUEST_DELAY: float = app_configuration.REQUEST_DELAY
    RETRYABLE_STATUS_CODES: set[int] = {
        HTTPStatus.INTERNAL_SERVER_ERROR,  # 500
        HTTPStatus.BAD_GATEWAY,  # 502
        HTTPStatus.SERVICE_UNAVAILABLE,  # 503
        HTTPStatus.GATEWAY_TIMEOUT,  # 504
    }
    USER_AGENT: str = app_configuration.USER_AGENT
    MERGE_REQUESTS_FIELD_MAPPING: Dict[str, str] = {}

    def __init__(self):
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=self.DEFAULT_TIMEOUT, headers={"User-Agent": self.USER_AGENT}
        )

    async def close(self) -> None:
        """Closes the persistent HTTP client."""
        await self.client.aclose()

    def _log(
        self,
        level: LogLevel,
        message: str,
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Central logging method that appends logs with timestamp and level to the job log.
        Logs are stored in the job log.
        """
        timestamp = datetime.now().isoformat()
        formatted_message = f"{timestamp} - {level.name} - {message}"
        if job_logger:
            job_logger(formatted_message)

    def _log_progress(
        self,
        current: int,
        total: int,
        stage: str,
        job_logger: Optional[Callable[[str], None]] = None,
        last_logged_percent: Optional[dict] = None,
    ) -> None:
        """
        Logs the progress of a specific stage (e.g. fetching or processing).
        Only logs at new 10% increments or on completion.
        """
        if total <= 0:
            return  # Avoid division by zero

        progress = min((current / total) * 100, 100)
        rounded = int(progress // 10) * 10

        # Log at every new 10%-step and always at 100%
        should_log = False
        if last_logged_percent is not None:
            last = last_logged_percent.get("value", -1)
            if rounded > last:
                should_log = True
            # Always log at 100% if not already logged
            if current == total and rounded != last:
                should_log = True
        else:
            should_log = True

        if should_log:
            self._log(
                LogLevel.INFO,
                f"{stage} progress: {progress:.0f}% ({min(current, total)}/{total}) completed.",
                job_logger,
            )
            if last_logged_percent is not None:
                last_logged_percent["value"] = rounded

    @staticmethod
    def _is_retryable_error(exc: BaseException) -> bool:
        """
        Determines if an exception should trigger a retry.
        """
        if isinstance(exc, RequestError):
            return True
        if isinstance(exc, HTTPStatusError):
            return (
                exc.response
                and exc.response.status_code in BaseFetcher.RETRYABLE_STATUS_CODES
            )
        return False

    async def _send_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> httpx.Response:
        """
        Sends an HTTP request with retry logic and returns the response.
        """
        self._log(
            LogLevel.DEBUG, f"Sending {method.upper()} request to {url}", job_logger
        )

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
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    headers=headers,
                    auth=auth,
                )
                self._check_response_status(response)
                return response
            except Exception as e:
                self._log(LogLevel.ERROR, f"HTTP request failed: {e}", job_logger)
                raise

        try:
            return await _request_with_retry()
        except Exception as e:
            self._log(
                LogLevel.EXCEPTION,
                f"Request failed after retries: {str(e)}",
                job_logger,
            )
            raise

    def _check_response_status(self, response: httpx.Response) -> None:
        """
        Validates HTTP response status.
        Raises formatted errors with context for debugging.
        """
        if response.status_code != HTTPStatus.OK:
            error_msg = (
                f"HTTP Error {response.status_code}\n"
                f"URL: {response.url}\n"
                f"Response: {response.text[:500]}..."  # Truncate long responses
            )
            self._log(LogLevel.ERROR, error_msg)
            raise HTTPStatusError(
                error_msg, request=response.request, response=response
            )

    async def _handle_rate_limit(
        self,
        headers: Dict[str, Any],
        job_logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Handle rate limits with Retry-After header fallback."""
        retry_after = headers.get("Retry-After", self.REQUEST_DELAY)
        try:
            delay = max(float(retry_after), self.REQUEST_DELAY)
        except (ValueError, TypeError):
            delay = self.REQUEST_DELAY

        self._log(
            LogLevel.WARNING, f"Rate limited. Resuming after {delay:.1f}s", job_logger
        )
        await asyncio.sleep(delay)

    @staticmethod
    def _validate_response_data(
        response: httpx.Response, job_logger: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Ensure valid response structure and handle edge cases."""
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Unexpected response format")
            return data
        except Exception:
            if job_logger:
                job_logger(f"Invalid JSON response: {response.text[:200]}")
            raise

    def _extract_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        Extracts a nested field from a dictionary based on a field path.
        """
        keys = field_path.split(".")
        for key in keys:
            if isinstance(data, list):
                return [
                    self._extract_nested_field(item, ".".join(keys[1:]))
                    for item in data
                ]
            if not isinstance(data, dict):
                return None
            data = data.get(key)
            if data is None:
                return None
        return data

    def parse_field(
        self,
        data: Dict[str, Any],
        field_name: str,
        requested_fields: List[str],
        data_type: DataType,
        mapping: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Parses a field based on the requested fields and its value in the data.
        """
        if field_name not in requested_fields:
            return None

        actual_key = mapping.get(field_name, field_name) if mapping else field_name
        value = self._extract_nested_field(data, actual_key)

        if value is None:
            return self._get_default_value(data_type)

        if data_type == DataType.LIST and not isinstance(value, list):
            return [value]
        return value

    @staticmethod
    def _get_default_value(data_type: DataType) -> Any:
        """Returns a default value based on the specified data type."""
        defaults = {
            DataType.STRING: "",
            DataType.INTEGER: 0,
            DataType.BOOLEAN: False,
            DataType.LIST: [],
            DataType.DICT: {},
        }
        return defaults.get(data_type, None)

    def parse_repo_data(
        self,
        data: Dict[str, Any],
        fields: List[str],
        field_mapping: Dict[str, str],
        merge_requests: List[MergeRequestData],
    ) -> RepoData:
        """
        Parses repository data into a RepoData based on the field mapping and requested fields.
        """
        repo_data = {
            key: self.parse_field(data, key, fields, DataType.STRING, field_mapping)
            for key in ["name", "fullName", "description", "createdAt", "updatedAt"]
        }
        repo_data["starCount"] = self.parse_field(
            data, "starCount", fields, DataType.INTEGER, field_mapping
        )
        repo_data["languages"] = self.parse_field(
            data, "languages", fields, DataType.LIST, field_mapping
        )

        return RepoData(**repo_data, mergeRequests=merge_requests)

    def parse_merge_requests(
        self,
        data: List[Dict[str, Any]],
        fields: List[str],
        field_mapping: Dict[str, str],
    ) -> List[MergeRequestData]:
        """
        Parses merge request data into a list of MergeRequestData based on field mapping and requested fields.
        """
        if not data:
            return []

        merge_request_fields = [
            field.split(".", 1)[1]
            for field in fields
            if field.startswith("mergeRequests.")
        ]
        return [
            MergeRequestData(
                authorName=self.parse_field(
                    mr,
                    "authorName",
                    merge_request_fields,
                    DataType.STRING,
                    field_mapping,
                ),
                createdAt=self.parse_field(
                    mr,
                    "createdAt",
                    merge_request_fields,
                    DataType.STRING,
                    field_mapping,
                ),
                description=self.parse_field(
                    mr,
                    "description",
                    merge_request_fields,
                    DataType.STRING,
                    field_mapping,
                ),
                title=self.parse_field(
                    mr, "title", merge_request_fields, DataType.STRING, field_mapping
                ),
            )
            for mr in data
        ]

    async def _request_with_token_rotation(
        self,
        token_pool: TokenPool,
        make_request_fn: Callable[[str], Any],
        job_logger: Optional[Callable[[str], None]] = None,
        ban_on_errors: Optional[List[str]] = None,
        max_attempts: Optional[int] = None,
    ) -> Any:
        """
        Handles token rotation and banning.
        """
        last_exception = None
        tokens_to_try = list(token_pool.tokens)
        ban_on_errors = ban_on_errors or [
            "rate limit",
            "authentication",
            "unauthorized",
        ]
        max_attempts = max_attempts or len(tokens_to_try)

        for _ in range(max_attempts):
            token = token_pool.get_token()
            if not token:
                raise RuntimeError(
                    "No tokens available for requests (all are exhausted)."
                )

            try:
                return await make_request_fn(token)
            except Exception as e:
                error_str = str(e).lower()
                should_ban = any(err in error_str for err in ban_on_errors)
                if should_ban:
                    self._log(
                        LogLevel.WARNING,
                        f"Token banned due to error: {e} | Token: {token}",
                        job_logger,
                    )
                    token_pool.ban_token(token)
                else:
                    self._log(
                        LogLevel.WARNING,
                        f"Token failed (not banned): {e} | Token: {token}",
                        job_logger,
                    )
                last_exception = e
                continue

        raise RuntimeError(f"All tokens failed. Last error: {last_exception}")
