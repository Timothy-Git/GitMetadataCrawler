import pytest

from backend.fetchers.graphql.gitlab_fetcher import GitLabFetcher
from backend.graphql.git_types import FetcherSettingsInput
from backend.utils.token_pool import TokenPool


@pytest.fixture
def gitlab_base_url():
    """Fixture for the base URL of the GitLab GraphQL API."""
    return "https://gitlab.example.com/api/graphql"


@pytest.fixture
def github_token_pool():
    """Fixture for a mock GitLab API token pool."""
    return TokenPool(["dummy_token"])


@pytest.fixture
def gitlab_fetcher():
    """Fixture for creating a GitLabFetcher instance."""
    return GitLabFetcher(base_url=gitlab_base_url, token_pool=github_token_pool)


@pytest.fixture
def mock_gitlab_fetcher_settings():
    """Fixture for mock settings for the GitLabFetcher."""
    return FetcherSettingsInput(
        searchTerm="test", programmingLanguage="Python", repoCount=5, maxMRs=3
    )


@pytest.fixture
def mock_gitlab_repositories():
    """Fixture for mock repositories for GitLabFetcher tests."""
    return {
        "data": {
            "projects": {
                "nodes": [
                    {
                        "name": "Repo1",
                        "description": "A test repository",
                        "starCount": 50,
                        "createdAt": "2025-01-01T00:00:00Z",
                        "updatedAt": "2025-06-01T00:00:00Z",
                        "languages": [{"name": "Python"}],
                        "mergeRequests": {
                            "nodes": [
                                {
                                    "author": {"name": "Author1"},
                                    "createdAt": "2025-01-02T00:00:00Z",
                                    "description": "Fix issue #123",
                                    "title": "Fix issue",
                                }
                            ]
                        },
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
    }
