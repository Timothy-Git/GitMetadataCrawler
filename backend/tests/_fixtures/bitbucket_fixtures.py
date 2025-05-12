import pytest

from backend.fetchers.rest_api.bitbucket_fetcher import BitbucketFetcher
from backend.graphql.git_types import FetcherSettingsInput


@pytest.fixture
def bitbucket_base_url():
    """Fixture for the base URL of the Bitbucket API."""
    return "https://api.bitbucket.org/2.0"


@pytest.fixture
def bitbucket_fetcher(bitbucket_base_url):
    """Fixture for creating a BitbucketFetcher instance."""
    return BitbucketFetcher(base_url=bitbucket_base_url)


@pytest.fixture
def mock_bitbucket_fetcher_settings():
    """Fixture for FetcherSettingsInput for Bitbucket."""
    return FetcherSettingsInput(
        searchTerm=None, repoCount=5, maxMRs=10, programmingLanguage="Python"
    )


@pytest.fixture
def mock_bitbucket_repositories():
    """Fixture for mock Bitbucket repository data."""
    return [
        {
            "name": "Repo1",
            "description": "Test repo",
            "language": "Python",
            "created_on": "2025-01-01",
            "updated_on": "2025-01-02",
            "links": {
                "pullrequests": {
                    "href": "https://api.bitbucket.org/2.0/repositories/repo1/pullrequests"
                }
            },
        },
        {
            "name": "Repo2",
            "description": "Test repo 2",
            "language": "Python",
            "created_on": "2025-01-01",
            "updated_on": "2025-01-02",
            "links": {
                "pullrequests": {
                    "href": "https://api.bitbucket.org/2.0/repositories/repo2/pullrequests"
                }
            },
        },
    ]
