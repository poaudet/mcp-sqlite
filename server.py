import os
import re
import sqlite3
from contextlib import closing

from mcp.server.fastmcp import FastMCP

DB_PATH = os.environ.get("DB_PATH", "/data/db.sqlite")
READ_ONLY = os.environ.get("READ_ONLY", "false").lower() in ("1", "true", "yes")
MAX_ROWS = int(os.environ.get("MAX_ROWS", "200"))

mcp = FastMCP(
    "sqlite",
    host="0.0.0.0",
    port=8000,
    streamable_http_path="/mcp",
)

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_READ_QUERY_ACTIONS = {
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_RECURSIVE,
}


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if READ_ONLY:
        conn.execute("PRAGMA query_only = ON")
    return conn


def _check_ident(name: str) -> str:
    if not _IDENT.fullmatch(name):
        raise ValueError(f"Invalid identifier: {name!r}")
    return name


@mcp.tool()
def list_tables() -> list[str]:
    """List all user tables in the SQLite database."""
    with closing(_conn()) as c:
        rows = c.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()
    return [r["name"] for r in rows]


@mcp.tool()
def describe_table(table: str) -> list[dict]:
    """Return column definitions for a table (name, type, notnull, pk, default)."""
    table = _check_ident(table)
    with closing(_conn()) as c:
        rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    if not rows:
        raise ValueError(f"Table not found: {table}")
    return [dict(r) for r in rows]


@mcp.tool()
def read_query(sql: str, limit: int = MAX_ROWS) -> dict:
    """Run a read-only SELECT and return rows as JSON objects.

    Only SELECT / WITH statements are allowed. Results are capped at `limit` rows.
    """
    stmt = sql.strip().lower()
    if not (stmt.startswith("select") or stmt.startswith("with")):
        raise ValueError("Only SELECT / WITH statements are allowed here.")

    limit = max(1, min(int(limit), 1000))
    with closing(_conn()) as c:
        c.set_authorizer(
            lambda action, _arg1, _arg2, _database, _trigger: (
                sqlite3.SQLITE_OK
                if action in _READ_QUERY_ACTIONS
                else sqlite3.SQLITE_DENY
            )
        )
        cur = c.execute(sql)
        rows = cur.fetchmany(limit + 1)

    truncated = len(rows) > limit
    rows = rows[:limit]
    return {
        "columns": [d[0] for d in cur.description] if cur.description else [],
        "rows": [dict(r) for r in rows],
        "row_count": len(rows),
        "truncated": truncated,
    }


@mcp.tool()
def write_query(sql: str) -> dict:
    """Run INSERT / UPDATE / DELETE / DDL. Returns rows affected.

    Disabled when READ_ONLY=true.
    """
    if READ_ONLY:
        raise PermissionError("Server is in READ_ONLY mode; writes are disabled.")

    with closing(_conn()) as c:
        cur = c.execute(sql)
        c.commit()
        return {
            "ok": True,
            "rowcount": cur.rowcount,
            "lastrowid": cur.lastrowid,
        }


@mcp.tool()
def create_table(name: str, columns_sql: str) -> str:
    """Create a table. `columns_sql` is the body, e.g. 'id INTEGER PRIMARY KEY, name TEXT'."""
    if READ_ONLY:
        raise PermissionError("Server is in READ_ONLY mode; writes are disabled.")
    name = _check_ident(name)
    with closing(_conn()) as c:
        c.execute(f"CREATE TABLE IF NOT EXISTS {name} ({columns_sql})")
        c.commit()
    return f"Table {name} ready."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
