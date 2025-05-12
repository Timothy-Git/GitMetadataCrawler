from http import HTTPStatus
from unittest.mock import patch, Mock, AsyncMock

import httpx
import pytest

from backend.graphql.git_types import RepoData, MergeRequestData
from backend.tests._helper.fetcher_test_helper import FetcherTestHelper


class TestBitbucketFetcher(FetcherTestHelper):
    """Test suite for the BitbucketFetcher class."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        bitbucket_fetcher,
        mock_bitbucket_fetcher_settings,
        mock_bitbucket_repositories,
        mock_merge_requests,
    ):
        self.fetcher = bitbucket_fetcher
        self.settings = mock_bitbucket_fetcher_settings
        self.fields = [
            "name",
            "description",
            "languages",
            "mergeRequests.authorName",
            "mergeRequests.description",
        ]
        self.mock_repositories = mock_bitbucket_repositories
        self.mock_merge_requests = mock_merge_requests

    @pytest.mark.parametrize(
        "search_term, programming_language, expected_query",
        [
            ("git", None, 'name~"git"'),
            ("git", "java", 'name~"git"&language~"java"'),
            (None, "python", 'language~"python"'),
            (None, None, ""),
            ("test", "c++", 'name~"test"&language~"c++"'),
        ],
    )
    def test_build_query_params(
        self, search_term, programming_language, expected_query
    ):
        """Test the _build_query_params method with various inputs."""
        filters = {
            "name~": f'"{search_term}"' if search_term else None,
            "language~": f'"{programming_language}"' if programming_language else None,
        }
        query_params = self.fetcher._build_query_params(filters)
        assert query_params == expected_query, (
            f"Expected query '{expected_query}', but got '{query_params}'."
        )

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    @patch(
        "backend.fetchers.rest_api.bitbucket_fetcher.BitbucketFetcher._ensure_authenticated"
    )
    async def test_fetch_projects_success(self, mock_ensure_authenticated, mock_get):
        """Test fetch_projects with a valid response."""
        mock_ensure_authenticated.return_value = None

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock(return_value=None)
        mock_response.json = Mock(return_value={"values": self.mock_repositories})
        mock_get.return_value = mock_response

        expected_repos = [
            RepoData(
                name="Repo1",
                description="Test repo",
                starCount=None,
                createdAt="2025-01-01",
                updatedAt="2025-01-02",
                languages=["Python"],
                mergeRequests=[],
            ),
            RepoData(
                name="Repo2",
                description="Test repo 2",
                starCount=None,
                createdAt="2025-01-01",
                updatedAt="2025-01-02",
                languages=["Python"],
                mergeRequests=[],
            ),
        ]

        result = await self.fetcher.fetch_projects(self.settings, self.fields)

        assert len(result) == len(self.mock_repositories[: self.settings.repoCount]), (
            f"Expected {len(self.mock_repositories[: self.settings.repoCount])} repositories but got {len(result)}."
        )

        result_sorted = sorted(result, key=lambda repo: repo.name)
        expected_sorted = sorted(expected_repos, key=lambda repo: repo.name)

        for actual_repo, expected_repo in zip(result_sorted, expected_sorted):
            self._assert_repo_data(actual_repo, expected_repo)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    @patch(
        "backend.fetchers.rest_api.bitbucket_fetcher.BitbucketFetcher._ensure_authenticated"
    )
    async def test_fetch_projects_no_repositories(
        self, mock_ensure_authenticated, mock_get
    ):
        """Test fetch_projects when no repositories are returned."""
        mock_ensure_authenticated.return_value = None

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock(return_value=None)
        mock_response.json = Mock(return_value={"values": []})
        mock_get.return_value = mock_response

        result = await self.fetcher.fetch_projects(self.settings, self.fields)

        assert result == [], "Expected no repositories to be returned."

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    @patch(
        "backend.fetchers.rest_api.bitbucket_fetcher.BitbucketFetcher._ensure_authenticated"
    )
    async def test_fetch_projects_invalid_response(
        self, mock_ensure_authenticated, mock_get
    ):
        """Test fetch_projects with an invalid response structure."""
        mock_ensure_authenticated.return_value = None

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock(return_value=None)
        mock_response.json = Mock(return_value={"invalid": "data"})  # Invalid structure
        mock_get.return_value = mock_response

        with pytest.raises(
            ValueError,
            match="The API response does not contain the expected 'values' key.",
        ):
            await self.fetcher.fetch_projects(self.settings, self.fields)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    @patch(
        "backend.fetchers.rest_api.bitbucket_fetcher.BitbucketFetcher._ensure_authenticated"
    )
    async def test_fetch_projects_with_merge_requests(
        self, mock_ensure_authenticated, mock_get
    ):
        """Test fetch_projects with repositories that include merge requests."""
        mock_ensure_authenticated.return_value = None

        # Mock the HTTP response for repositories
        mock_response_repos = Mock()
        mock_response_repos.raise_for_status = Mock(return_value=None)
        mock_response_repos.json = Mock(return_value={"values": self.mock_repositories})
        mock_get.return_value = mock_response_repos

        # Mock the HTTP response for merge requests
        mock_merge_request_data = [
            MergeRequestData(
                authorName="John Doe",
                createdAt="2025-01-01T12:00:00Z",
                description="Test merge request",
                title="Add new feature",
            )
        ]
        with patch(
            "backend.fetchers.rest_api.bitbucket_fetcher.BitbucketFetcher._fetch_merge_requests",
            AsyncMock(return_value=mock_merge_request_data),
        ) as mock_fetch_merge_requests:
            # Ensure "mergeRequests" is included in the fields
            self.fields.append("mergeRequests")

            result = await self.fetcher.fetch_projects(self.settings, self.fields)

            # Ensure the fetcher is called for each repository
            assert mock_fetch_merge_requests.call_count == len(
                self.mock_repositories[: self.settings.repoCount]
            ), (
                f"Expected _fetch_merge_requests to be called {len(self.mock_repositories[: self.settings.repoCount])} times, "
                f"but it was called {mock_fetch_merge_requests.call_count} times."
            )

            # Validate the result
            assert len(result) == len(
                self.mock_repositories[: self.settings.repoCount]
            ), (
                f"Expected {len(self.mock_repositories[: self.settings.repoCount])} repositories but got {len(result)}."
            )
            assert len(result[0].mergeRequests) > 0, (
                "Expected at least one merge request in the first repository."
            )
            assert (
                result[0].mergeRequests[0].authorName
                == mock_merge_request_data[0].authorName
            )

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    @patch(
        "backend.fetchers.rest_api.bitbucket_fetcher.BitbucketFetcher._ensure_authenticated"
    )
    async def test_fetch_projects_with_empty_response(
        self, mock_ensure_authenticated, mock_get
    ):
        """Test fetch_projects when the API returns an empty response."""
        mock_ensure_authenticated.return_value = None

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock(return_value=None)
        mock_response.json = Mock(return_value={})  # Empty response
        mock_get.return_value = mock_response

        with pytest.raises(
            ValueError,
            match="The API response does not contain the expected 'values' key.",
        ):
            await self.fetcher.fetch_projects(self.settings, self.fields)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_fetch_projects_with_invalid_authentication(self, mock_post):
        """Test fetch_projects when authentication fails."""
        # Mock the response object
        mock_response = Mock()
        mock_response.status_code = HTTPStatus.UNAUTHORIZED
        mock_response.text = "Unauthorized"

        # Mock the post method to raise an HTTPStatusError
        mock_post.return_value = mock_response
        mock_post.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )

        with pytest.raises(httpx.HTTPStatusError, match="Unauthorized"):
            await self.fetcher._authenticate(
                self.fetcher.token_url,
                self.fetcher.client_id,
                self.fetcher.client_secret,
                job_logger=None,
            )
