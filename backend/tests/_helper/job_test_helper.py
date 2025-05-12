import asyncio

from backend.graphql.enums import StateEnum, FetchJobMode
from backend.graphql.git_types import (
    FetcherSettingsInput,
    RequestedFieldInput,
    RepoData,
    MergeRequestData,
)
from backend.graphql.mutation import Mutation
from backend.graphql.query import Query


class JobTestHelper:
    def setup_method(self):
        self.created_jobs = []

    def teardown_method(self):
        mutation = Mutation()
        for job_id in self.created_jobs:
            try:
                mutation.delete_fetch_job(job_id=job_id)
            except Exception as e:
                print(f"Failed to delete job {job_id}: {e}")

    async def wait_for_job_completion(self, job_id, timeout=180):
        query = Query()
        start = asyncio.get_event_loop().time()
        while True:
            jobs = query.get_fetch_jobs(job_id=job_id)
            if jobs:
                job = jobs[0]
                if job.state not in [StateEnum.RUNNING, StateEnum.CREATED]:
                    return job
            if asyncio.get_event_loop().time() - start > timeout:
                raise TimeoutError(
                    f"Job {job_id} did not finish within {timeout} seconds"
                )
            await asyncio.sleep(0.5)

    def generate_job_data(
        self,
        platform,
        repo_count=5,
        max_mrs=2,
        search_term="",
        programming_language="",
        requested_fields=None,
    ):
        if requested_fields is None:
            requested_fields = [
                RequestedFieldInput(field="name"),
                RequestedFieldInput(field="fullName"),
                RequestedFieldInput(field="description"),
                RequestedFieldInput(field="starCount"),
                RequestedFieldInput(field="languages"),
                RequestedFieldInput(
                    field="mergeRequests", subfields=["authorName", "description"]
                ),
            ]
        return {
            "name": f"{platform.name} Repos",
            "mode": FetchJobMode.ASSISTANT,
            "platform": platform,
            "fetcher_settings": FetcherSettingsInput(
                repoCount=repo_count,
                maxMRs=max_mrs,
                searchTerm=search_term,
                programmingLanguage=programming_language,
            ),
            "requested_fields": requested_fields,
        }

    def expand_requested_fields(self, requested_fields):
        expanded_fields = set()
        for field in requested_fields:
            if (
                hasattr(field, "field")
                and field.field == "mergeRequests"
                and getattr(field, "subfields", None)
            ):
                for subfield in field.subfields:
                    expanded_fields.add(f"mergeRequests.{subfield}")
            elif hasattr(field, "field"):
                expanded_fields.add(field.field)
            else:
                expanded_fields.add(field)
        return expanded_fields

    def validate_requested_fields(self, repo, requested_fields):
        for field in RepoData.__annotations__.keys():
            value = getattr(repo, field, None)
            if field == "mergeRequests":
                continue
            if field in requested_fields:
                assert value is not None, (
                    f"Field '{field}' is in requestedFields but is None."
                )
            else:
                assert value is None, (
                    f"Field '{field}' is not in requestedFields but is populated: {value}."
                )
        if repo.mergeRequests:
            for mr in repo.mergeRequests:
                for field in MergeRequestData.__annotations__.keys():
                    full_field_name = f"mergeRequests.{field}"
                    if full_field_name in requested_fields:
                        value = getattr(mr, field, None)
                        assert value is not None, (
                            f"Field '{full_field_name}' is in requestedFields but is None."
                        )
                    else:
                        value = getattr(mr, field, None)
                        assert value is None, (
                            f"Field '{full_field_name}' is not in requestedFields but is populated: {value}."
                        )
