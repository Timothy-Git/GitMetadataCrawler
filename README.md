# GitMetadataCrawler

This project is a tool for collecting and analyzing metadata from GitHub, GitLab, and Bitbucket repositories using their APIs.

## Installation

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

Add your tokens to the `.env` file. Multiple tokens can be separated with a comma, e.g. “xyz123, xyz456”.

## Quick Start

1. **Start the server:**
   ```sh
   cd backend/app
   python main.py
   ```
   The API will be available at `http://localhost:5000/graphql`.

2. **Run tests:**
   ```sh
   pytest
   ```

## How It Works

With this tool, you can create fetch jobs using your own settings (like which platform, how many repositories and which fields to collect). After creating a job, you can start it, watch its progress in the logs, and when it’s done, export the results as a CSV file or analyze them with plugins.

You can use GraphQL mutations like `createFetchJob` to create a new fetch job, and `startFetchJob` to begin collecting data. For more details and example queries, see the [docs/crawler_graphql_commands/](docs/crawler_graphql_commands/jobs) folder. An example is shown for each operation. In addition, the documentation of the scheme contains more detailed explanations.