# Readwise DB Manager

Readwise DB Manager is a Python application equipped with both a Tkinter graphical user interface (GUI) and a Command-Line Interface (CLI). It allows you to fetch, manage, and search your saved documents, articles, and highlights from the Readwise API. Furthermore, it seamlessly syncs your data to both PostgreSQL and Snowflake databases and features an AI-powered assistant to query your saved collection.

<img width="1000" height="729" alt="image" src="https://github.com/user-attachments/assets/ffb10a6e-a842-452b-bb92-f6b5d5f4ad8d" />


---

## Features

- Readwise API Integration: Fetch documents, highlights, and articles filtered by location (new, later, archive, feed), category (article, tweet, note, etc.), and date.
- Database Synchronization:

    - PostgreSQL: Pulls existing records and appends new ones smoothly, skipping duplicates.

    - Snowflake: Pushes new records to a cloud data warehouse using temporary tables and merge operations.
- Advanced Search: * Exact Word Search: Standard string matching.

  - Fuzzy Search: Uses fuzzywuzzy to find similar matches even with typos or incomplete queries.
- Ask AI: Integrates with OpenAI's gpt-4.1-mini to analyze and answer contextual questions based on your latest Readwise articles.

## Demo videos

### Readwise app demo 1
<video src="https://github.com/user-attachments/assets/43e0efd9-a4cf-49b1-88c3-38f579ada3e9" controls width="700"></video>

### Readwise app demo 2
<video src="https://github.com/user-attachments/assets/160354be-2554-4bcb-8462-bcce70ed99f2" controls width="700"></video>
---

## Prerequisites

Ensure you have Python 3.8+ installed. You will also need active accounts/instances for:

- Readwise (API Token required)
- OpenAI (API Key required)
- PostgreSQL Database
- Snowflake Data Cloud


---
## Project structure

```text
.
├── main.py                     # Tkinter desktop app
├── back_end.py                 # Shared backend utilities + CLI-style workflow
├── database.py                 # Postgres / Snowflake helpers
├── request_data_interaction.py # Data cleanup and transformation
├── user_request.py             # Readwise API request logic
└── config.py                   # API URL
```

---

## Environment variables

Create a `.env` file in the project root.

```env
READWISE_TOKEN=your_readwise_token
LOGS_DIR=./logs

PGRES_DB_NAME=your_postgres_db
PGRES_DB_USER=your_postgres_user
PGRES_DB_PASSWORD=your_postgres_password

SF_USERNAME=your_snowflake_username
SF_PASSWORD=your_snowflake_password
SF_ACCOUNT=your_snowflake_account
SF_WAREHOUSE=your_snowflake_warehouse

# Optional, if your OpenAI client reads it from the environment
OPENAI_API_KEY=your_openai_api_key
```

---

## Database expectations

### Postgres

The code expects a table named `readwise_articles` with columns:

- `title`
- `url`
- `summary`
- `time_saved`
- `date_saved`

Because the insert query uses `ON CONFLICT (url) DO NOTHING`, the `url` column should be unique.

Example schema:

```sql
CREATE TABLE IF NOT EXISTS readwise_articles (
    title TEXT,
    url TEXT PRIMARY KEY,
    summary TEXT,
    time_saved TEXT,
    date_saved TIMESTAMP
);
```

### Snowflake

The Snowflake write path expects a database/schema/table layout like this:

- database: `READWISE_ARTICLES`
- schema: `PUBLIC`
- target table: `READWISE_ARTICLES`

The app uploads the current DataFrame to a temporary table named `TEMP_NEW_DATA`, then merges on `URL`.

---

## Running the app

Start the GUI:

```bash
python main.py
```

### In the UI

- API Settings: Choose the location, category, and how many days back you want to search, then click Fetch from API.

- Data Table: Double-click any row in the table to open the article's URL directly in your default web browser.

- Actions: Use the search bar for Word or Fuzzy searches, or type a question and click Ask AI to have GPT analyze the currently loaded articles.

- Save: Click Save to DBs to push new entries to both Postgres and Snowflake.

- Double-click any row to open its URL in your browser.

---

## Future improvements

Next steps:

- Add database migration/setup scripts.
- Expose all supported Readwise categories in the GUI.
- Improve duplicate handling.
- Package the app for desktop distribution.

---

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License.

