from unittest.mock import patch
import pytest


class TestGitLabFetcher:
    """Test suite for the GitLabFetcher class."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        gitlab_fetcher,
        mock_gitlab_fetcher_settings,
        mock_gitlab_repositories,
        mock_merge_requests,
    ):
        """Set up shared resources for GitLabFetcher tests."""
        self.fetcher = gitlab_fetcher
        self.settings = mock_gitlab_fetcher_settings
        self.fields = ["name", "description", "languages", "mergeRequests.authorName"]
        self.mock_repositories = mock_gitlab_repositories
        self.mock_merge_requests = mock_merge_requests

    async def _fetch_and_validate_projects(
        self, mock_make_request, expected_count, expected_repo_name
    ):
        """Helper to fetch and validate repository projects."""
        result = await self.fetcher.fetch_projects(self.settings, self.fields)
        assert len(result) == expected_count, (
            f"Expected {expected_count} repository(-ies), but got {len(result)}."
        )
        if expected_count > 0:
            repo = result[0]
            assert repo.name == expected_repo_name, (
                f"Expected repository name '{expected_repo_name}', got '{repo.name}'."
            )
            assert repo.starCount == 50, "Star count mismatch in the repository."
            if isinstance(repo.languages, list):
                actual_languages = [
                    lang if isinstance(lang, str) else lang.get("name", "")
                    for lang in repo.languages
                ]
            else:
                actual_languages = (
                    [repo.languages.get("name", "")]
                    if isinstance(repo.languages, dict)
                    else []
                )
            assert "Python" in actual_languages, (
                f"Expected 'Python' as the primary language, got '{actual_languages}'."
            )
            assert len(repo.mergeRequests) == 1, (
                "Mismatch in the number of merge requests."
            )

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.gitlab_fetcher.GitLabFetcher._make_request")
    async def test_fetch_projects_success(self, mock_make_request):
        """Test fetch_projects with valid repositories."""
        mock_make_request.return_value = self.mock_repositories
        self.fields.append("starCount")
        await self._fetch_and_validate_projects(
            mock_make_request, expected_count=1, expected_repo_name="Repo1"
        )

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.gitlab_fetcher.GitLabFetcher._make_request")
    async def test_fetch_projects_invalid_response(self, mock_make_request):
        """Test fetch_projects with an invalid response structure."""
        mock_make_request.return_value = {"invalid": "data"}
        with pytest.raises(RuntimeError, match="Invalid response structure."):
            await self.fetcher.fetch_projects(self.settings, self.fields)

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.gitlab_fetcher.GitLabFetcher._make_request")
    async def test_fetch_projects_no_repositories(self, mock_make_request):
        """Test fetch_projects when no repositories are returned."""
        mock_make_request.return_value = {
            "data": {
                "projects": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
        with pytest.raises(RuntimeError, match="No repositories found."):
            await self.fetcher.fetch_projects(self.settings, self.fields)

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.gitlab_fetcher.GitLabFetcher._make_request")
    async def test_fetch_projects_non_dict_response(self, mock_make_request):
        """Test fetch_projects with a non-dict response."""
        mock_make_request.return_value = None
        with pytest.raises(
            RuntimeError,
            match="Failed to fetch repositories: Invalid response structure",
        ):
            await self.fetcher.fetch_projects(self.settings, self.fields)

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.gitlab_fetcher.GitLabFetcher._make_request")
    async def test_fetch_projects_pagination(self, mock_make_request):
        """Test fetch_projects with paginated results."""
        # First page with hasNextPage=True
        mock_make_request.side_effect = [
            {
                "data": {
                    "projects": {
                        "nodes": [{"name": "Repo1"}],
                        "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR1"},
                    }
                }
            },
            # Second page with hasNextPage=False
            {
                "data": {
                    "projects": {
                        "nodes": [{"name": "Repo2"}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            },
        ]
        result = await self.fetcher.fetch_projects(self.settings, self.fields)
        repo_names = [getattr(repo, "name", None) for repo in result]
        assert "Repo1" in repo_names and "Repo2" in repo_names

    @pytest.mark.asyncio
    async def test_execute_raw_query_empty(self):
        """Test execute_raw_query with empty query."""
        with pytest.raises(ValueError, match="The raw query must not be empty."):
            await self.fetcher.execute_raw_query("")

    @pytest.mark.asyncio
    @patch("backend.fetchers.graphql.gitlab_fetcher.GitLabFetcher._make_request")
    async def test_execute_raw_query_invalid_response(self, mock_make_request):
        """Test execute_raw_query with invalid response."""
        mock_make_request.return_value = "invalid"
        with pytest.raises(
            RuntimeError, match="Failed to execute raw query on GitLab."
        ):
            await self.fetcher.execute_raw_query("query { dummy }")
