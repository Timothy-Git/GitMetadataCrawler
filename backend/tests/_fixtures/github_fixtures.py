import pytest

from backend.fetchers.graphql.github_fetcher import GitHubFetcher
from backend.graphql.git_types import FetcherSettingsInput
from backend.utils.token_pool import TokenPool


@pytest.fixture
def github_base_url():
    """Fixture for the base URL of the GitHub GraphQL API."""
    return "https://api.github.com/graphql"


@pytest.fixture
def github_token_pool():
    """Fixture for a mock GitHub API token pool."""
    return TokenPool(["dummy_token"])


@pytest.fixture
def github_fetcher():
    """Fixture for creating a GitHubFetcher instance."""
    return GitHubFetcher(base_url=github_base_url, token_pool=github_token_pool)


@pytest.fixture
def github_fetcher_settings():
    """Fixture for FetcherSettingsInput for GitHub."""
    return FetcherSettingsInput(
        repoCount=2, maxMRs=2, searchTerm="test", programmingLanguage="Python"
    )


@pytest.fixture
def github_fields():
    """Fixture for the default fields used in GitHubFetcher tests."""
    return ["name", "description", "starCount", "languages", "mergeRequests"]


@pytest.fixture
def mock_github_repositories():
    """Fixture for mock GitHub repository data."""
    return [
        {
            "name": "repo1",
            "description": "A test repository",
            "stargazers": {"totalCount": 5},
            "primaryLanguage": {"name": "Python"},
            "pullRequests": {
                "nodes": [
                    {
                        "author": {"login": "user1"},
                        "createdAt": "2025-01-01",
                        "bodyText": "Test pull request",
                        "title": "Fix issue",
                        "reactions": {"totalCount": 2},
                    }
                ]
            },
        }
    ]


@pytest.fixture
def mock_github_response_invalid():
    """Fixture for an invalid GitHub GraphQL API response."""
    return {"data": None}


@pytest.fixture
def mock_github_response_success():
    """Fixture for a successful GitHub GraphQL API response."""
    return {
        "data": {
            "search": {
                "edges": [
                    {
                        "node": {
                            "name": "repo1",
                            "description": "A test repository",
                            "stargazers": {"totalCount": 5},
                            "primaryLanguage": {"name": "Python"},
                            "pullRequests": {
                                "nodes": [
                                    {
                                        "author": {"login": "user1"},
                                        "createdAt": "2025-01-01",
                                        "bodyText": "Test pull request",
                                        "title": "Fix issue",
                                        "reactions": {"totalCount": 2},
                                    }
                                ]
                            },
                        }
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
    }
