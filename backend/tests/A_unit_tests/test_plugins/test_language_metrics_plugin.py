import os
import pandas as pd

from backend.graphql.enums import FetchJobMode, PlatformEnum
from backend.plugins.language_metrics_plugin import (
    language_metrics_plugin,
    collect_language_metrics,
)
from backend.graphql.git_types import FetchJob, StateEnum


def test_collect_language_metrics(repo_data_language_metrics):
    metrics = collect_language_metrics(repo_data_language_metrics)
    assert metrics.total_repos == 2
    assert metrics.language_usage["Python"] == 1
    assert metrics.language_usage["JavaScript"] == 1
    assert metrics.language_usage["Java"] == 1
    assert metrics.single_language_repo_count["Java"] == 1
    assert metrics.multi_language_repo_count["Python"] == 1
    assert metrics.multi_language_repo_count["JavaScript"] == 1
    assert tuple(sorted(["Python", "JavaScript"])) in metrics.combination_count


def test_language_metrics_plugin_local_export(tmp_path, fetch_job_language_metrics):
    result = language_metrics_plugin(fetch_job_language_metrics, local_export=True)
    assert result.urls
    for plugin_url in result.urls:
        assert os.path.exists(plugin_url.url)
        df = pd.read_csv(plugin_url.url, sep=";")
        assert not df.empty
        os.remove(plugin_url.url)


def test_language_metrics_plugin_server_export(fetch_job_language_metrics):
    result = language_metrics_plugin(fetch_job_language_metrics, local_export=False)
    assert result.urls
    for plugin_url in result.urls:
        assert plugin_url.url.startswith("http://") or plugin_url.url.startswith(
            "https://"
        )


def test_language_metrics_plugin_empty_data():
    empty_job = FetchJob(
        jobId="empty_job",
        name="Empty Job",
        mode=FetchJobMode.ASSISTANT,
        repoData=[],
        platform=PlatformEnum.GITHUB,
        state=StateEnum.SUCCESSFUL,
    )
    result = language_metrics_plugin(empty_job, local_export=True)
    assert result.urls == []
    assert "No repository data available" in result.message
