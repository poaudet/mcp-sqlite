# mcp-sqlite

A SQLite MCP server using Streamable HTTP at `/mcp`.

## Run with Docker Compose

```bash
mkdir -p data
cp /path/to/your.db data/db.sqlite  # optional; an empty database is created if missing
docker compose up -d --build
docker compose logs -f
```

Tagged releases (`v*`) are published to GitHub Container Registry as
`ghcr.io/poaudet/mcp-sqlite`, with both the release tag and `latest` tags.
To use the published image instead of building locally, pull it with:

```bash
docker pull ghcr.io/poaudet/mcp-sqlite:latest
```

The server listens on `http://localhost:8000/mcp`. Configure an MCP client with:

```json
{
  "mcpServers": {
    "sqlite": {
      "url": "http://localhost:8000/mcp",
      "transport": "http"
    }
  }
}
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `DB_PATH` | `/data/db.sqlite` | SQLite database file |
| `READ_ONLY` | `false` | Set to `true`, `1`, or `yes` to block writes |
| `MAX_ROWS` | `200` | Default maximum rows returned by `read_query` (capped at 1000) |

`list_tables`, `describe_table`, and `read_query` inspect the database.
`write_query` runs INSERT, UPDATE, DELETE, or DDL statements, and `create_table`
creates a table. `read_query` accepts SELECT/WITH queries only and enforces
read-only access. When `READ_ONLY` is enabled, SQLite query-only mode is also
enabled and the write tools are blocked.

The Docker image installs `mcp>=1.9.0,<2.0.0`, which supports
`transport="streamable-http"`.
