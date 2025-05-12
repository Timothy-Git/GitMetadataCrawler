import pytest
from backend.graphql.enums import FetchJobMode, PlatformEnum, StateEnum
from backend.graphql.git_types import FetchJob


@pytest.fixture
def repo_data_language_metrics():
    return [
        {
            "name": "Repo1",
            "fullName": "owner/repo1",
            "languages": ["Python", "JavaScript"],
            "mergeRequests": [
                {"authorName": "Alice", "title": "Fix bug"},
                {"authorName": "Bob", "title": "Add feature"},
            ],
        },
        {
            "name": "Repo2",
            "fullName": "owner/repo2",
            "languages": ["Java"],
            "mergeRequests": [{"authorName": "Charlie", "title": "Improve docs"}],
        },
    ]


@pytest.fixture
def fetch_job_language_metrics(repo_data_language_metrics):
    return FetchJob(
        jobId="test_job",
        name="Test Job",
        mode=FetchJobMode.ASSISTANT,
        repoData=repo_data_language_metrics,
        platform=PlatformEnum.GITHUB,
        state=StateEnum.SUCCESSFUL,
    )
