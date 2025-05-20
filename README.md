# GitMetadataCrawler 🚀
A universal tool for crawling Git repository metadata using GraphQL.

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![Issues](https://img.shields.io/github/issues/Timothy-Git/GitMetadataCrawler)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)

---

## Table of Contents

- [Abstract](#abstract)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Getting API Tokens](#getting-api-tokens)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Extending and Contributing](#extending-and-contributing)
  - [Adding a New Fetcher](#adding-a-new-fetcher)
  - [Adding New Fields](#adding-new-fields)
  - [Creating New Plugins](#creating-new-plugins)

---

## Abstract

The collection of research data in software development is a central challenge. The intention of my work is to universally collect metadata of repositories from different Git platforms, process it in a standardized way and make it available to researchers for further analysis. To achieve this, a tool is being developed that enables user-specific queries using GraphQL.

## Installation

**Clone the repository:**
```sh
git clone https://github.com/Timothy-Git/GitMetadataCrawler
```

**(Recommended) Create a virtual environment:**

On **Linux/macOS**:
```sh
python -m venv venv
source venv/bin/activate
```

On **Windows**:
```sh
python -m venv venv
venv\Scripts\activate
```
> **Note:**  
> If you encounter a policy error when trying to activate the virtual environment, you may need to adjust your local execution policy.  
> Open PowerShell and run:
> ```sh
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**Install dependencies:**
```sh
pip install -r backend/requirements.txt
```

## Configuration

Before running the project, you need to set up some environment variables. The most important settings are:

- **MongoDB:**  
  Set `MONGO_URI` to your MongoDB connection string (e.g. `mongodb://localhost:27017`).

- **API Tokens:**  
  You need API tokens for GitHub, GitLab, and Bitbucket to fetch data.

- **Export Path:**  
  Set `EXPORT_PATH` to choose where exported CSV files will be saved (e.g. `EXPORT_PATH=./exports`).

### Getting API Tokens

- **GitHub:**  
  Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens) and create a new token.

- **GitLab:**  
  Go to [GitLab Profile > Access Tokens](https://gitlab.com/-/user_settings/personal_access_tokens) and generate a token.

- **Bitbucket:**  
  Go to [Bitbucket Settings > OAuth consumers](https://bitbucket.org/gitmetadatacrawler_example/workspace/settings/api) and create an OAuth consumer.

Add your tokens to the `.env` file. Multiple tokens can be separated with a comma, e.g. `xyz123, xyz456`.

## Quick Start

1. **Start the server:**
   ```sh
   python backend/app/main.py
   ```
   The API will be available at `http://localhost:5000/graphql`.

2. **Run tests:**
   ```sh
   pytest
   ```

## How It Works

With this tool, you can create fetch jobs using your own settings (like which platform, how many repositories and which fields to collect). After creating a job, you can start it, watch its progress in the logs, and when it’s done, export the results as a CSV file or analyze them with plugins.

You can use GraphQL mutations like `createFetchJob` to create a new fetch job, and `startFetchJob` to begin collecting data. For more details and example queries, see the [docs/crawler_graphql_commands/](docs/crawler_graphql_commands/jobs) folder. An example is shown for each operation. In addition, the documentation of the scheme contains more detailed explanations.

## Extending and Contributing

The GitMetadataCrawler is designed to be flexible and easy to extend. Whether you want to add support for new platforms, introduce additional fields or develop your own plugins for data analysis.

### Adding a New Fetcher

To support a new Git platform, navigate to the `/fetchers` directory and choose the correct architecture (REST API or GraphQL). Create a new fetcher class based on the existing examples and ensure that it inherits from the base architecture fetcher that you have chosen.
After implementing your fetcher, update the `PlatformEnum` to include your new platform and add the correct mapping in the `FetcherFactory`.  
Keep in mind that you may also need to add new configuration entries for API keys and the platform’s `base_url` in your environment settings.

### Adding New Fields

If you want to collect additional metadata fields, extend the `RepoData` type to include your new fields. Then, update the mapping tables in each fetcher so that the fetchers know how to extract these fields from their platform APIs.

### Creating New Plugins

To develop a new plugin for custom analysis or export, use the `/plugins` directory. You can use the example plugin `language_metrics_plugin.py` as a template. There are no strict limitations on what plugins can do. 
Each plugin should provide an entry-point function, which is registered with the `PluginRegistry.register` method. You can also add a description for your plugin, which will be visible in the GraphQL schema.  

---

Feel free to open issues or submit pull requests if you have ideas or improvements!
