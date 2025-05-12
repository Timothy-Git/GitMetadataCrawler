import os
import pandas as pd
import pytest

from backend.graphql.enums import PlatformEnum, StateEnum
from backend.graphql.mutation import Mutation
from backend.tests._helper.job_test_helper import JobTestHelper
from backend.utils.plugin_enum import PluginEnum


class TestExportAndPlugin(JobTestHelper):
    """Integration tests for CSV export and plugin execution."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "platform", [PlatformEnum.GITLAB, PlatformEnum.GITHUB, PlatformEnum.BITBUCKET]
    )
    async def test_csv_export_and_language_metrics_plugin(self, platform):
        mutation = Mutation()
        job_data = self.generate_job_data(
            platform, repo_count=10, max_mrs=1, programming_language="java"
        )
        created_job = mutation.create_fetch_job(**job_data)
        self.created_jobs.append(created_job.jobId)
        await mutation.start_fetch_job(job_id=created_job.jobId)
        job_status = await self.wait_for_job_completion(created_job.jobId)
        assert job_status.state == StateEnum.SUCCESSFUL

        # Test CSV export (local)
        file_path = mutation.export_csv(job_id=created_job.jobId, local_export=True)
        assert os.path.exists(file_path)
        df = pd.read_csv(file_path, sep=";")
        assert not df.empty
        os.remove(file_path)

        # Test CSV export (server URL)
        file_url = mutation.export_csv(job_id=created_job.jobId, local_export=False)
        assert file_url.startswith("http://") or file_url.startswith("https://")

        # Test plugin execution (local)
        plugin_result = mutation.execute_plugin(
            job_id=created_job.jobId,
            plugin=PluginEnum.LANGUAGE_METRICS,
            local_export=True,
        )
        assert plugin_result.urls
        for plugin_url in plugin_result.urls:
            assert os.path.exists(plugin_url.url)
            df = pd.read_csv(plugin_url.url, sep=";")
            assert not df.empty
            os.remove(plugin_url.url)

    def test_requested_field_input_properties(self):
        from backend.graphql.git_types import RequestedFieldInput

        rfi = RequestedFieldInput(
            field="mergeRequests", subfields=["authorName", "description"]
        )
        assert hasattr(rfi, "field")
        assert hasattr(rfi, "subfields")
        assert rfi.field == "mergeRequests"
        assert isinstance(rfi.subfields, list)
        assert "authorName" in rfi.subfields
        assert "description" in rfi.subfields
