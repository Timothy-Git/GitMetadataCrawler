from unittest.mock import patch
import pytest
from backend.graphql.git_types import RepoData
from backend.tests._helper.fetcher_test_helper import FetcherTestHelper


class TestGitHubFetcher(FetcherTestHelper):
    """Test suite for the GitHubFetcher class."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        github_fetcher,
        github_fetcher_settings,
        github_fields,
        mock_github_repositories,
        mock_merge_requests,
    ) -> None:
        self.fetcher = github_fetcher
        self.settings = github_fetcher_settings
        self.fields = github_fields
        self.mock_repositories = mock_github_repositories
        self.mock_merge_requests = mock_merge_requests

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.github_fetcher.GitHubFetcher._make_request")
    async def test_fetch_projects_success(
        self, mock_make_request, mock_github_response_success
    ) -> None:
        mock_make_request.return_value = mock_github_response_success

        result = await self.fetcher.fetch_projects(self.settings, self.fields)
        expected_repo = [
            RepoData(
                name="repo1",
                description="A test repository",
                starCount=5,
                createdAt=None,
                updatedAt=None,
                languages=["Python"],
                mergeRequests=[],
            )
        ]

        result_set = {repo.name for repo in result}
        expected_set = {repo.name for repo in expected_repo}

        assert result_set == expected_set, (
            f"Expected repositories {expected_set} but got {result_set}."
        )

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.github_fetcher.GitHubFetcher._make_request")
    async def test_invalid_response_structure(
        self, mock_make_request, mock_github_response_invalid
    ) -> None:
        mock_make_request.return_value = mock_github_response_invalid

        with pytest.raises(
            RuntimeError, match="Failed to fetch projects: Invalid response structure."
        ):
            await self.fetcher.fetch_projects(self.settings, self.fields)

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.github_fetcher.GitHubFetcher._make_request")
    async def test_fetch_projects_non_dict_response(self, mock_make_request):
        mock_make_request.return_value = None  # or any invalid type
        with pytest.raises(RuntimeError, match="Failed to fetch projects:"):
            await self.fetcher.fetch_projects(self.settings, self.fields)

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.github_fetcher.GitHubFetcher._make_request")
    async def test_fetch_projects_pagination(self, mock_make_request):
        # First page with hasNextPage=True
        mock_make_request.side_effect = [
            {
                "data": {
                    "search": {
                        "edges": [{"node": {"name": "repo1"}}],
                        "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR1"},
                    }
                }
            },
            # Second page with hasNextPage=False
            {
                "data": {
                    "search": {
                        "edges": [{"node": {"name": "repo2"}}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            },
        ]
        result = await self.fetcher.fetch_projects(self.settings, self.fields)
        repo_names = [getattr(repo, "name", None) for repo in result]
        assert "repo1" in repo_names and "repo2" in repo_names

    def test_build_query_with_cursor(self):
        query = self.fetcher.build_query(
            self.settings, self.fields, after_cursor="CURSOR"
        )
        assert 'after: "CURSOR"' in query

    @pytest.mark.asyncio
    async def test_execute_raw_query_empty(self):
        with pytest.raises(ValueError, match="The raw query must not be empty."):
            await self.fetcher.execute_raw_query("")

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.github_fetcher.GitHubFetcher._make_request")
    async def test_execute_raw_query_invalid_response(self, mock_make_request):
        mock_make_request.return_value = "invalid"
        with pytest.raises(
            RuntimeError, match="Failed to execute raw query on GitHub."
        ):
            await self.fetcher.execute_raw_query("query { dummy }")
