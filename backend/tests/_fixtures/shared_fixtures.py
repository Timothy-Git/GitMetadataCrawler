import pytest

from backend.graphql.git_types import MergeRequestData, RepoData


@pytest.fixture
def mock_merge_requests():
    """Fixture for mock merge request data."""
    return [
        MergeRequestData(
            authorName="Author1",
            createdAt="2025-01-01",
            description="MR description",
            title="Test MR",
        )
    ]


@pytest.fixture
def mock_repo_data(mock_merge_requests):
    """Fixture for a mock RepoData instance."""
    return RepoData(
        name="Repo1",
        description="A test repository",
        languages=["Python"],
        mergeRequests=mock_merge_requests,
    )
