import pytest
from bson import ObjectId

from backend.database.jobs import (
    create_job,
    update_job,
    get_job,
    get_all_jobs,
    delete_job,
)
from backend.graphql.enums import PlatformEnum, StateEnum, FetchJobMode
from backend.graphql.git_types import FetchJob, FetcherSettings


class TestDbJobs:
    """Unit tests for job database CRUD and edge cases."""

    def _create_multiple_jobs(self, mock_collection, sample_fetch_job, count=2):
        """Helper to create multiple jobs in the database."""
        for _ in range(count):
            create_job(sample_fetch_job, collection=mock_collection)

    # ===========================
    # CRUD Tests
    # ===========================

    def test_create_job(self, mock_collection, sample_fetch_job):
        """Should create a job and store it in the database."""
        job_id = create_job(sample_fetch_job, collection=mock_collection)
        job = mock_collection.find_one({"_id": ObjectId(job_id)})
        assert job is not None
        assert job["_id"] == ObjectId(job_id)
        assert job["name"] == sample_fetch_job.name
        assert job["state"] == StateEnum.CREATED.value
        assert job["platform"] == PlatformEnum.GITHUB.value

    def test_update_job(self, mock_collection, create_sample_job):
        """Should update an existing job's fields."""
        sample_fetch_job, job_id = create_sample_job
        sample_fetch_job.name = "Updated Job Name"
        update_job(sample_fetch_job, collection=mock_collection)
        updated_job = mock_collection.find_one({"_id": ObjectId(job_id)})
        assert updated_job["name"] == "Updated Job Name"

    def test_get_job(self, mock_collection, create_sample_job):
        """Should retrieve a job by its ID."""
        sample_fetch_job, job_id = create_sample_job
        job = get_job(job_id, collection=mock_collection)
        assert job is not None
        assert job.name == sample_fetch_job.name
        assert job.state == sample_fetch_job.state
        assert job.settings == sample_fetch_job.settings
        assert job.platform == sample_fetch_job.platform

    def test_get_all_jobs(self, mock_collection, sample_fetch_job):
        """Should retrieve all jobs from the collection."""
        self._create_multiple_jobs(mock_collection, sample_fetch_job, count=3)
        jobs = get_all_jobs(collection=mock_collection)
        assert len(jobs) == 3

    def test_delete_job(self, mock_collection, create_sample_job):
        """Should delete a job by its ID."""
        sample_fetch_job, job_id = create_sample_job
        success = delete_job(job_id, collection=mock_collection)
        assert success is True
        job = mock_collection.find_one({"_id": ObjectId(job_id)})
        assert job is None

    # ===========================
    # Error Handling Tests
    # ===========================

    def test_get_job_invalid_id(self, mock_collection):
        """Should raise ValueError for invalid jobId format."""
        with pytest.raises(ValueError, match="Invalid job ID format"):
            get_job("invalid_job_id", collection=mock_collection)

    def test_update_job_invalid_id(self, mock_collection, sample_fetch_job):
        """Should raise ValueError for invalid jobId format on update."""
        sample_fetch_job.jobId = "invalid_job_id"
        with pytest.raises(ValueError, match="Invalid job ID format"):
            update_job(sample_fetch_job, collection=mock_collection)

    def test_update_job_non_existent(self, mock_collection):
        """Should raise ValueError when updating a non-existent job."""
        invalid_job_id = str(ObjectId())
        sample_fetch_job = FetchJob(
            jobId=invalid_job_id,
            name="Non-existent Job",
            state=StateEnum.CREATED,
            mode=FetchJobMode.ASSISTANT,
            platform=PlatformEnum.GITHUB,
            startTime=None,
            settings=FetcherSettings(
                repoCount=10, maxMRs=5, searchTerm="test", programmingLanguage="Python"
            ),
            requestedFields=["name", "description"],
            repoData=[],
        )
        with pytest.raises(ValueError, match="Job not found with ID"):
            update_job(sample_fetch_job, collection=mock_collection)

    def test_delete_job_non_existent(self, mock_collection):
        """Should return False when deleting a non-existent job."""
        job_id = str(ObjectId())
        success = delete_job(job_id, collection=mock_collection)
        assert success is False

    # ===========================
    # Additional/Edge Case Tests
    # ===========================

    def test_delete_all_jobs(self, mock_collection, sample_fetch_job):
        """Should delete all jobs and return an empty list."""
        self._create_multiple_jobs(mock_collection, sample_fetch_job, count=3)
        mock_collection.delete_many({})
        jobs = get_all_jobs(collection=mock_collection)
        assert len(jobs) == 0

    def test_get_jobs_by_state(self, mock_collection, sample_fetch_job):
        """Should filter jobs by state."""
        sample_fetch_job.state = StateEnum.CREATED
        create_job(sample_fetch_job, collection=mock_collection)
        sample_fetch_job.state = StateEnum.RUNNING
        create_job(sample_fetch_job, collection=mock_collection)
        created_jobs = [
            job
            for job in get_all_jobs(collection=mock_collection)
            if job.state == StateEnum.CREATED
        ]
        running_jobs = [
            job
            for job in get_all_jobs(collection=mock_collection)
            if job.state == StateEnum.RUNNING
        ]
        assert len(created_jobs) == 1
        assert len(running_jobs) == 1

    def test_get_jobs_by_platform(self, mock_collection, sample_fetch_job):
        """Should filter jobs by platform."""
        sample_fetch_job.platform = PlatformEnum.GITHUB
        create_job(sample_fetch_job, collection=mock_collection)
        sample_fetch_job.platform = PlatformEnum.GITLAB
        create_job(sample_fetch_job, collection=mock_collection)
        github_jobs = [
            job
            for job in get_all_jobs(collection=mock_collection)
            if job.platform == PlatformEnum.GITHUB
        ]
        gitlab_jobs = [
            job
            for job in get_all_jobs(collection=mock_collection)
            if job.platform == PlatformEnum.GITLAB
        ]
        assert len(github_jobs) == 1
        assert len(gitlab_jobs) == 1
