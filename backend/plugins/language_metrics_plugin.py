from dataclasses import dataclass, field
from typing import Dict, Set, Tuple, List

from backend.graphql.git_types import FetchJob, PluginResult, PluginUrl
from backend.utils.plugin_registry import PluginRegistry
from backend.utils.csv_exporter import CSVExporter
from itertools import combinations


@dataclass
class LanguageMetrics:
    language_repo_count: Dict[str, Set[str]] = field(default_factory=dict)
    language_usage: Dict[str, int] = field(default_factory=dict)
    single_language_repo_count: Dict[str, int] = field(default_factory=dict)
    multi_language_repo_count: Dict[str, int] = field(default_factory=dict)
    combination_count: Dict[Tuple[str, str], int] = field(default_factory=dict)
    total_repos: int = 0
    total_language_mentions: int = 0


def collect_language_metrics(repo_data: List[Dict]) -> LanguageMetrics:
    metrics = LanguageMetrics()
    for repo in repo_data:
        repo_name = repo.get("name", "unknown")
        languages = repo.get("languages") or []
        metrics.total_language_mentions += len(languages)
        for lang in languages:
            metrics.language_repo_count.setdefault(lang, set()).add(repo_name)
            metrics.language_usage[lang] = metrics.language_usage.get(lang, 0) + 1
        if len(languages) == 1:
            metrics.single_language_repo_count[languages[0]] = (
                metrics.single_language_repo_count.get(languages[0], 0) + 1
            )
        elif len(languages) > 1:
            for lang in languages:
                metrics.multi_language_repo_count[lang] = (
                    metrics.multi_language_repo_count.get(lang, 0) + 1
                )
            for lang1, lang2 in combinations(sorted(set(languages)), 2):
                metrics.combination_count[(lang1, lang2)] = (
                    metrics.combination_count.get((lang1, lang2), 0) + 1
                )
    metrics.total_repos = len(repo_data)
    return metrics


def language_metrics_plugin(job: FetchJob, local_export: bool = False) -> PluginResult:
    """
    Calculates statistics for each programming language across the fetched repositories.

    Metrics per language:
    - repoCount: Number of repositories using the language.
    - percentOfRepos: Percentage of all repositories using the language.
    - percentOfMentions: Percentage of all language mentions that are this language.
    - singleLanguageRepoCount: Number of repositories where this language is the only language.
    - multiLanguageRepoCount: Number of repositories where this language appears together with others.

    Additionally:
    - combinationCount: For each language pair, how often they appear together in a repository.

    Two CSV files are exported:
    1. language_metrics: Main statistics for languages.
    2. language_combinations: The number of language pairs appearing together.

    If local_export is False (default), CSVs are hosted on the server and URLs are returned.
    If local_export is True, CSVs are saved in the export path (see .env) and local file paths are returned.
    """
    if not job.repoData:
        return PluginResult(urls=[], message="No repository data available.")

    metrics = collect_language_metrics(job.repoData)

    # Prepare main language statistics
    results = []
    for lang, repos in sorted(
        metrics.language_repo_count.items(), key=lambda x: len(x[1]), reverse=True
    ):
        repo_count = len(repos)
        percent_of_repos = (
            (repo_count / metrics.total_repos * 100) if metrics.total_repos else 0
        )
        percent_of_mentions = (
            (metrics.language_usage[lang] / metrics.total_language_mentions * 100)
            if metrics.total_language_mentions
            else 0
        )
        results.append(
            {
                "language": lang,
                "repoCount": repo_count,
                "percentOfRepos": f"{round(percent_of_repos, 2)} %",
                "percentOfMentions": f"{round(percent_of_mentions, 2)} %",
                "singleLanguageRepoCount": metrics.single_language_repo_count.get(
                    lang, 0
                ),
                "multiLanguageRepoCount": metrics.multi_language_repo_count.get(
                    lang, 0
                ),
            }
        )

    # Predefined file names
    metrics_csv_name = f"language_metrics_{job.jobId}.csv"
    combination_csv_name = f"language_combinations_{job.jobId}.csv"

    # Export main statistics as CSV
    file_path = CSVExporter.export_plugin_data_to_csv(
        results, job.jobId, local_export=local_export, file_name=metrics_csv_name
    )
    language_metrics_csv = (
        file_path if local_export else CSVExporter.generate_file_url(file_path)
    )

    # Prepare language combination statistics
    combination_results = [
        {"language1": lang1, "language2": lang2, "combinationCount": count}
        for (lang1, lang2), count in sorted(
            metrics.combination_count.items(), key=lambda x: x[1], reverse=True
        )
    ]

    urls = {"language_metrics_csv": language_metrics_csv}
    message = "Language plugin CSVs exported."
    if combination_results:
        combination_file_path = CSVExporter.export_plugin_data_to_csv(
            combination_results,
            job.jobId,
            local_export=local_export,
            file_name=combination_csv_name,
        )
        combination_value = (
            combination_file_path
            if local_export
            else CSVExporter.generate_file_url(combination_file_path)
        )
        urls["combination_csv"] = combination_value
        message += " Language combination CSV exported."

    return PluginResult(
        urls=[PluginUrl(name=k, url=v) for k, v in urls.items()], message=message
    )


language_metrics_plugin.description = "Calculates statistics for each programming language across the fetched repositories"
PluginRegistry.register("LANGUAGE_METRICS", language_metrics_plugin)
