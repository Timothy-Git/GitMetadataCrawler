import os
from datetime import datetime
from tempfile import gettempdir
from typing import List, Dict, Optional

import pandas as pd

from backend.app.config import app_configuration


def get_export_path() -> str:
    """
    Returns the export path from configuration or uses the system temp directory.
    """
    export_path = getattr(app_configuration, "EXPORT_PATH", None)
    if export_path and os.path.isdir(export_path):
        return export_path
    return gettempdir()


def get_unique_file_path(directory: str, file_name: str) -> str:
    """
    Returns a unique file path in the given directory by appending _01, _02, etc. if needed.
    """
    base, ext = os.path.splitext(file_name)
    candidate = os.path.join(directory, file_name)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}_{counter:02d}{ext}")
        counter += 1
    return candidate


class CSVExporter:
    @staticmethod
    def export_repo_data_to_csv(
        repo_data: List[Dict], job_id: str, local_export: bool = False
    ) -> str:
        """
        Exports fetch data to a CSV file.
        If local_export is False (default), saves in temp dir (overwrites if exists) and returns the file URL.
        If local_export is True, saves in export path and returns the local file path.
        """
        if not repo_data:
            raise ValueError("No repository data available for export.")

        flattened_data = [CSVExporter.flatten_dict(repo) for repo in repo_data]
        df = pd.DataFrame(flattened_data)
        df = df.dropna(axis=1, how="all")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        file_name = f"fetch_job_{job_id}_{timestamp}.csv"
        if not local_export:
            export_dir = gettempdir()
            file_path = os.path.join(export_dir, file_name)  # Overwrite if exists
        else:
            export_dir = get_export_path()
            file_path = get_unique_file_path(export_dir, file_name)

        df.to_csv(file_path, index=False, sep=";", encoding="utf-8-sig")

        if not local_export:
            return CSVExporter.generate_file_url(file_path)
        else:
            return file_path

    @staticmethod
    def export_plugin_data_to_csv(
        data: List[Dict],
        job_id: str,
        local_export: bool = False,
        file_name: Optional[str] = None,
    ) -> str:
        """
        Exports plugin generated data to a CSV file.
        If local_export is False (default), saves in temp dir (overwrites if exists) and returns the file URL.
        If local_export is True, saves in export path (with _01, _02, ...) and returns the local file path.
        You can optionally specify a custom file_name (should include .csv).
        """
        if not data:
            raise ValueError("No data available for export.")

        df = pd.DataFrame(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        if not file_name:
            file_name = f"plugin_data_{job_id}_{timestamp}.csv"
        else:
            # If no .csv is given, append .csv
            if not file_name.lower().endswith(".csv"):
                file_name += ".csv"

        if not local_export:
            export_dir = gettempdir()
            file_path = os.path.join(export_dir, file_name)  # Overwrite if exists
        else:
            export_dir = get_export_path()
            file_path = get_unique_file_path(export_dir, file_name)

        df.to_csv(file_path, index=False, sep=";", encoding="utf-8-sig")

        if not local_export:
            return CSVExporter.generate_file_url(file_path)
        else:
            return file_path

    @staticmethod
    def generate_file_url(file_path: str) -> str:
        """
        Generates a URL for the given file path.
        """
        file_name = os.path.basename(file_path)
        return f"http://{app_configuration.SERVER_HOST}:{app_configuration.SERVER_PORT}/files/{file_name}"

    @staticmethod
    def flatten_dict(data: Dict, parent_key: str = "", sep: str = ".") -> Dict:
        """
        Flattens nested dictionaries and lists into a flat dictionary with indexed keys.
        """
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(CSVExporter.flatten_dict(value, new_key, sep=sep).items())
            elif isinstance(value, list):
                for i, item in enumerate(value, start=1):
                    if isinstance(item, dict):
                        items.extend(
                            CSVExporter.flatten_dict(
                                item, f"{new_key}_{i}", sep=sep
                            ).items()
                        )
                    elif item is not None:
                        items.append((f"{new_key}_{i}", item))
            elif value is not None:
                items.append((new_key, value))
        return dict(items)
