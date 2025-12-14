"""Helper - SQL database operations.

Provides utilities for downloading and querying SQLite databases.
"""

import sqlite3
import tempfile
from pathlib import Path

import httpx


async def download_and_query(url: str, query: str) -> list:
    """Download SQL/SQLite file and run query.

    Handles both SQLite database files and raw SQL text files.
    For SQL text files, creates an in-memory database and executes the schema.

    Args:
        url: URL to SQL/SQLite file.
        query: SQL query to execute.

    Returns:
        list: Query results as list of tuples.

    Example:
        >>> results = await download_and_query(
        ...     "https://example.com/db.sql",
        ...     "SELECT COUNT(*) FROM users WHERE age > 18"
        ... )
        >>> print(results[0][0])
        42

    Note:
        Tries to open as SQLite database first, falls back to
        treating as SQL text file if that fails.
    """
    # Download file
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=60)
        content = resp.content

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(content)
        db_path = f.name

    # Try as SQLite database first, then as SQL text file
    try:
        # Try as SQLite database first
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(query)
        results = cursor.fetchall()
        conn.close()
    except Exception:
        # Try as SQL text file - create in-memory DB
        conn = sqlite3.connect(":memory:")
        sql_text = content.decode("utf-8")
        conn.executescript(sql_text)
        cursor = conn.execute(query)
        results = cursor.fetchall()
        conn.close()

    # Cleanup
    Path(db_path).unlink(missing_ok=True)

    return results


def query_db(db_path: str, query: str) -> list:
    """Query existing SQLite database.

    Args:
        db_path: Path to SQLite database file.
        query: SQL query to execute.

    Returns:
        list: Query results as list of tuples.

    Example:
        >>> results = query_db("data.db", "SELECT * FROM users LIMIT 5")
        >>> print(len(results))
        5
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results
