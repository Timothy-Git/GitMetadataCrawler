import pytest

from backend.graphql.enums import FetchJobMode, PlatformEnum, StateEnum
from backend.graphql.git_types import (
    RequestedFieldInput,
)
from backend.graphql.mutation import Mutation
from backend.graphql.query import Query
from backend.tests._helper.job_test_helper import JobTestHelper


class TestFetcherJobs(JobTestHelper):
    """Test class for fetcher job functionality."""

    def setup_method(self):
        """Initialize resources for tests."""
        self.created_jobs = []  # Track created jobs for cleanup

    def teardown_method(self):
        """Clean up resources after tests."""
        mutation = Mutation()
        for job_id in self.created_jobs:
            try:
                mutation.delete_fetch_job(job_id=job_id)
            except Exception as e:
                print(f"Failed to delete job {job_id}: {e}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "platform", [PlatformEnum.GITLAB, PlatformEnum.GITHUB, PlatformEnum.BITBUCKET]
    )
    async def test_fetcher_job_pipeline(self, platform):
        """Test the complete fetcher job pipeline."""
        mutation = Mutation()

        # Create a job
        job_data = self.generate_job_data(platform, repo_count=5, max_mrs=5)
        created_job = mutation.create_fetch_job(**job_data)
        self.created_jobs.append(created_job.jobId)
        assert created_job.jobId is not None, "Job ID should not be None."
        assert created_job.name == f"{platform.name} Repos", "Job name mismatch."

        # Start the job
        started_job = await mutation.start_fetch_job(job_id=created_job.jobId)
        assert started_job.jobId == created_job.jobId, "Started job ID mismatch."
        assert started_job.state == StateEnum.RUNNING, "Job state should be RUNNING."

        # Wait for the job to complete
        job_status = await self.wait_for_job_completion(created_job.jobId)
        assert job_status.state == StateEnum.SUCCESSFUL, (
            f"Job failed with state: {job_status.state}"
        )
        assert len(job_status.repoData) == job_data["fetcher_settings"].repoCount, (
            f"Expected {job_data['fetcher_settings'].repoCount} repositories, "
            f"but got {len(job_status.repoData)}."
        )

        # Validate that only requested fields are inside
        requested_fields = self.expand_requested_fields(job_data["requested_fields"])
        for repo in job_status.repoData:
            self.validate_requested_fields(repo, requested_fields)

    @pytest.mark.asyncio
    async def test_create_fetch_job_invalid_mode(self):
        """Test creating a fetch job with an invalid mode."""
        mutation = Mutation()
        with pytest.raises(ValueError, match="Expert mode requires a raw query"):
            mutation.create_fetch_job(
                name="Invalid Job",
                mode=FetchJobMode.EXPERT,
                platform=PlatformEnum.GITHUB,
                raw_query=None,
            )

    @pytest.mark.asyncio
    async def test_stop_fetch_job(self):
        """Test stopping a running fetch job."""
        mutation = Mutation()
        job_data = self.generate_job_data(
            PlatformEnum.GITHUB, repo_count=5, max_mrs=2
        )
        created_job = mutation.create_fetch_job(**job_data)
        self.created_jobs.append(created_job.jobId)
        started_job = await mutation.start_fetch_job(job_id=created_job.jobId)

        stopped_job = await mutation.stop_fetch_job(job_id=started_job.jobId)
        assert stopped_job.state == StateEnum.STOPPED, "Job state should be STOPPED."

    @pytest.mark.asyncio
    async def test_get_fetch_jobs(self):
        """Test retrieving fetch jobs."""
        query = Query()
        mutation = Mutation()
        job_data = self.generate_job_data(
            PlatformEnum.GITHUB, repo_count=5, max_mrs=2
        )
        created_job = mutation.create_fetch_job(**job_data)
        self.created_jobs.append(created_job.jobId)

        jobs = query.get_fetch_jobs(job_id=created_job.jobId)
        assert len(jobs) == 1, "Expected exactly one job."
        assert jobs[0].jobId == created_job.jobId, "Job ID mismatch."

    @pytest.mark.asyncio
    async def test_fetcher_job_with_missing_requested_fields(self):
        """Test fetcher job with a set of requested fields."""
        mutation = Mutation()

        # Create a job with limited requested fields
        job_data = self.generate_job_data(
            PlatformEnum.GITHUB,
            repo_count=5,
            max_mrs=1,
            requested_fields=[
                RequestedFieldInput(field="name"),
                RequestedFieldInput(field="description"),
            ],
        )
        created_job = mutation.create_fetch_job(**job_data)
        self.created_jobs.append(created_job.jobId)

        # Start the job
        await mutation.start_fetch_job(job_id=created_job.jobId)
        job_status = await self.wait_for_job_completion(created_job.jobId)

        # Validate that only the requested fields are populated
        requested_fields = self.expand_requested_fields(job_data["requested_fields"])
        for repo in job_status.repoData:
            self.validate_requested_fields(repo, requested_fields)

    @pytest.mark.asyncio
    async def test_fetcher_job_with_empty_repo_data(self):
        """Test fetcher job when no repositories are returned."""
        mutation = Mutation()

        # Create a job with a search term that yields no results
        job_data = self.generate_job_data(PlatformEnum.GITHUB, repo_count=0)
        created_job = mutation.create_fetch_job(**job_data)
        self.created_jobs.append(created_job.jobId)

        # Start the job
        await mutation.start_fetch_job(job_id=created_job.jobId)
        job_status = await self.wait_for_job_completion(created_job.jobId)

        # Validate that repoData is empty
        assert len(job_status.repoData) == 0, "Expected no repositories in repoData."

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "platform", [PlatformEnum.GITLAB, PlatformEnum.GITHUB, PlatformEnum.BITBUCKET]
    )
    async def test_fetcher_job_with_various_search_terms(self, platform):
        """Test fetcher jobs with different search terms and programming languages."""
        mutation = Mutation()
        # Test with only searchTerm
        job_data = self.generate_job_data(
            platform, repo_count=2, max_mrs=1, search_term="test"
        )
        created_job = mutation.create_fetch_job(**job_data)
        self.created_jobs.append(created_job.jobId)
        await mutation.start_fetch_job(job_id=created_job.jobId)
        job_status = await self.wait_for_job_completion(created_job.jobId)
        assert job_status.state == StateEnum.SUCCESSFUL

        # Test with only programmingLanguage
        job_data = self.generate_job_data(
            platform, repo_count=2, max_mrs=1, programming_language="python"
        )
        created_job2 = mutation.create_fetch_job(**job_data)
        self.created_jobs.append(created_job2.jobId)
        await mutation.start_fetch_job(job_id=created_job2.jobId)
        job_status2 = await self.wait_for_job_completion(created_job2.jobId)
        assert job_status2.state == StateEnum.SUCCESSFUL

        # Test with both searchTerm and programmingLanguage
        job_data = self.generate_job_data(
            platform,
            repo_count=2,
            max_mrs=1,
            search_term="example",
            programming_language="java",
        )
        created_job3 = mutation.create_fetch_job(**job_data)
        self.created_jobs.append(created_job3.jobId)
        await mutation.start_fetch_job(job_id=created_job3.jobId)
        job_status3 = await self.wait_for_job_completion(created_job3.jobId)
        assert job_status3.state == StateEnum.SUCCESSFUL
