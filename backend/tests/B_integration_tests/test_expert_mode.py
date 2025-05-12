import pytest
from backend.graphql.mutation import Mutation
from backend.graphql.enums import FetchJobMode, PlatformEnum, StateEnum
from backend.tests._helper.job_test_helper import JobTestHelper


@pytest.mark.asyncio
class TestExpertMode(JobTestHelper):
    RAW_QUERY_GITHUB = """
    {
      search(query: "stars:>100", type: REPOSITORY, first: 2) {
        edges {
          node {
            ... on Repository {
              name
              description
            }
          }
        }
      }
    }
    """

    RAW_QUERY_GITLAB = """
    {
      projects(first: 2, search: "gitlab") {
        nodes {
          name
          description
        }
      }
    }
    """

    @pytest.mark.parametrize(
        "platform,raw_query,should_succeed",
        [
            (PlatformEnum.GITHUB, RAW_QUERY_GITHUB, True),
            (PlatformEnum.GITLAB, RAW_QUERY_GITLAB, True),
            (PlatformEnum.BITBUCKET, RAW_QUERY_GITHUB, False),
        ],
    )
    async def test_create_and_execute_expert_job(
        self, platform, raw_query, should_succeed
    ):
        mutation = Mutation()

        job = mutation.create_fetch_job(
            name=f"ExpertModeTest_{platform.name}",
            mode=FetchJobMode.EXPERT,
            platform=platform,
            raw_query=raw_query,
        )
        self.created_jobs.append(job.jobId)
        await mutation.start_fetch_job(job_id=job.jobId)
        final_job = await self.wait_for_job_completion(job.jobId)

        if should_succeed:
            assert final_job.state == StateEnum.SUCCESSFUL, f"Job failed: {final_job}"
            assert final_job.repoData is not None, "repoData is None"
            assert len(final_job.repoData) > 0, "repoData is empty"
        else:
            assert final_job.state == StateEnum.FAILURE, (
                f"Expected failure, got {final_job.state}"
            )
            print(f"Job failed as expected: {final_job}")
