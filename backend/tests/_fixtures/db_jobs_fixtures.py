import mongomock
import pytest
from backend.graphql.enums import PlatformEnum, StateEnum, FetchJobMode
from backend.graphql.git_types import FetchJob, FetcherSettings


@pytest.fixture
def mock_collection():
    """Provides a fresh mocked MongoDB collection for each test."""
    client = mongomock.MongoClient()
    db = client["test_db"]
    collection = db["fetch_jobs"]
    yield collection


@pytest.fixture
def sample_fetch_job() -> FetchJob:
    """Returns a sample FetchJob instance."""
    settings = FetcherSettings(
        repoCount=10, maxMRs=5, searchTerm="test", programmingLanguage="Python"
    )
    return FetchJob(
        jobId="",  # Will be set after creation
        name="Test Job",
        state=StateEnum.CREATED,
        startTime=None,
        settings=settings,
        platform=PlatformEnum.GITHUB,
        mode=FetchJobMode.ASSISTANT,
        requestedFields=["name", "description"],
        repoData=[],
    )


@pytest.fixture
def create_sample_job(mock_collection, sample_fetch_job):
    """Creates a job in the mock collection and returns the job and its ID."""
    from backend.database.jobs import create_job

    job_id = create_job(sample_fetch_job, collection=mock_collection)
    sample_fetch_job.jobId = job_id
    return sample_fetch_job, job_id
