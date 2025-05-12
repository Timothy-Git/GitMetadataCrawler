import os
import pandas as pd
import pytest

from backend.utils.csv_exporter import CSVExporter


class TestCSVExporter:
    def test_flatten_dict(self):
        """
        Test the flatten_dict method with RepoData.
        """
        data = {
            "name": "Repo1",
            "fullName": "owner/repo1",
            "languages": ["Python", "JavaScript"],
            "mergeRequests": [
                {"authorName": "Alice", "title": "Fix bug"},
                {"authorName": "Bob", "title": "Add feature"},
            ],
            "description": None,
        }
        expected = {
            "name": "Repo1",
            "fullName": "owner/repo1",
            "languages_1": "Python",
            "languages_2": "JavaScript",
            "mergeRequests_1.authorName": "Alice",
            "mergeRequests_1.title": "Fix bug",
            "mergeRequests_2.authorName": "Bob",
            "mergeRequests_2.title": "Add feature",
        }
        result = CSVExporter.flatten_dict(data)
        assert result == expected

    def test_export_repo_data_to_csv_server(self, repo_export_data_simple):
        """Test export_repo_data_to_csv with server export (default)."""
        job_id = "test_job"
        file_url = CSVExporter.export_repo_data_to_csv(
            repo_export_data_simple, job_id, local_export=False
        )
        # The file is in tempdir, extract path from URL
        file_name = file_url.split("/")[-1]
        temp_dir = os.getenv("TMPDIR") or os.getenv("TEMP") or "/tmp"
        file_path = os.path.join(temp_dir, file_name)
        assert os.path.exists(file_path)
        df = pd.read_csv(file_path, sep=";")
        assert "name" in df.columns
        os.remove(file_path)

    def test_export_repo_data_to_csv_local(self, repo_export_data_simple):
        """Test export_repo_data_to_csv with local export (unique file name)."""
        job_id = "test_job"
        file_path = CSVExporter.export_repo_data_to_csv(
            repo_export_data_simple, job_id, local_export=True
        )
        assert os.path.exists(file_path)
        df = pd.read_csv(file_path, sep=";")
        assert "fullName" in df.columns
        os.remove(file_path)

    def test_export_plugin_data_to_csv_custom_name(self, repo_export_data_simple):
        """Test export_plugin_data_to_csv with custom file name."""
        job_id = "plugin_test"
        file_name = "custom_plugin_export.csv"
        file_path = CSVExporter.export_plugin_data_to_csv(
            repo_export_data_simple, job_id, local_export=True, file_name=file_name
        )
        assert file_path.endswith(file_name)
        assert os.path.exists(file_path)
        os.remove(file_path)

    def test_special_characters(self, repo_data_special_chars):
        """Test export_repo_data_to_csv with special characters."""
        job_id = "special_characters_job"
        file_path = CSVExporter.export_repo_data_to_csv(
            repo_data_special_chars, job_id, local_export=True
        )
        assert os.path.exists(file_path)
        df = pd.read_csv(file_path, sep=";")
        assert df.loc[0, "name"] == "Репозиторий"  # repository
        os.remove(file_path)

    def test_empty_repo_data(self, repo_data_empty):
        """Test export_repo_data_to_csv with empty repository data."""
        job_id = "empty_job"
        with pytest.raises(
            ValueError, match="No repository data available for export."
        ):
            CSVExporter.export_repo_data_to_csv(repo_data_empty, job_id)

    def test_plugin_data_to_csv_empty(self, repo_data_empty):
        """Test export_plugin_data_to_csv with empty data."""
        job_id = "empty_plugin"
        with pytest.raises(ValueError, match="No data available for export."):
            CSVExporter.export_plugin_data_to_csv(repo_data_empty, job_id)

    def test_unique_file_path_generation(self, repo_export_data_simple, tmp_path):
        """Test that unique file names are generated for local export if file exists."""
        job_id = "unique_test"
        # First export
        file_path1 = CSVExporter.export_repo_data_to_csv(
            repo_export_data_simple, job_id, local_export=True
        )
        # Second export should create a file with _01
        file_path2 = CSVExporter.export_repo_data_to_csv(
            repo_export_data_simple, job_id, local_export=True
        )
        assert file_path1 != file_path2
        assert os.path.exists(file_path1)
        assert os.path.exists(file_path2)
        os.remove(file_path1)
        os.remove(file_path2)
