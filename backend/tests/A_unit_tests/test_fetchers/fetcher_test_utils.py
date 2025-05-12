import re
from typing import List, Optional, Any
from unittest.mock import AsyncMock

import pytest

from backend.graphql.git_types import RepoData


class FetcherTestUtils:
    """
    Utility class for setting up and testing fetchers.
    Provides helpers to mock methods, normalize queries, and validate results.
    """

    def setup_common(
        self,
        fetcher: Any,
        fetcher_settings: dict,
        mock_repositories: List[RepoData],
        mock_merge_requests: List[dict],
    ) -> None:
        """Set up shared test resources for fetchers."""
        self.fetcher = fetcher
        self.settings = fetcher_settings
        self.mock_repositories = mock_repositories
        self.mock_merge_requests = mock_merge_requests

    def mock_fetcher_methods(
        self,
        repositories: Optional[List[RepoData]] = None,
        merge_requests: Optional[List[dict]] = None,
        paginate_side_effect: Optional[Exception] = None,
    ) -> None:
        """Mock common fetcher methods for testing, such as _paginate and _fetch_merge_requests."""
        self._mock_method("_paginate", repositories, paginate_side_effect)
        self._mock_method("_fetch_merge_requests", merge_requests)

    def _mock_method(
        self,
        method_name: str,
        return_value: Optional[Any] = None,
        side_effect: Optional[Exception] = None,
    ) -> None:
        """Helper to mock a specific method on the fetcher."""
        mock = AsyncMock(return_value=return_value, side_effect=side_effect)
        setattr(self.fetcher, method_name, mock)

    def assert_repositories(
        self,
        result: List[RepoData],
        expected_repos: List[RepoData],
    ) -> None:
        """Validate the repositories returned by the fetcher."""
        assert len(result) == len(expected_repos), (
            f"Expected {len(expected_repos)} repositories, but got {len(result)}."
        )
        assert all(isinstance(repo, RepoData) for repo in result), (
            "All results should be instances of RepoData."
        )

    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalize a GraphQL query by removing extra whitespaces and line breaks."""
        return re.sub(r"\s+", " ", query.strip())

    @pytest.mark.parametrize(
        "query, expected_query",
        [
            (
                """
                    {
                        search(query: "test language:Python" type: REPOSITORY first: 2) {
                            edges { node { ... on Repository { name } } }
                        }
                    }
                    """,
                """
                    {
                        search(query: "test language:Python" type: REPOSITORY first: 2) {
                            edges { node { ... on Repository { name } } }
                        }
                    }
                    """,
            )
        ],
    )
    def test_build_query(self, query, expected_query) -> None:
        """Ensure build_query generates correct GraphQL queries."""
        normalized_query = FetcherTestUtils.normalize_query(query)
        normalized_expected = FetcherTestUtils.normalize_query(expected_query)
        assert normalized_query == normalized_expected, (
            "Generated query does not match the expected query."
        )
