"""SQLite storage through the standard library (ADR 0003, spec GH-8 AC5).

The schema comes from the numbered scripts in `app/migrations/`. There is no
down-migration: a database file with a version this app doesn't know is refused,
and the demo file (synthetic data only) is reset by deleting it.
"""

import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Request

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_MIGRATION_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


class SchemaVersionError(RuntimeError):
    """The database file has a schema version this app doesn't know."""


def connect(path: Path) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced.

    `check_same_thread=False` because FastAPI may run a request's dependency and
    endpoint on different pool threads; each connection still serves one request only.
    """
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrations() -> list[tuple[int, Path]]:
    """The numbered migration scripts, in order (1, 2, …)."""
    found = []
    for script in MIGRATIONS_DIR.glob("*.sql"):
        match = _MIGRATION_NAME.match(script.name)
        if match:
            found.append((int(match.group(1)), script))
    found.sort()
    numbers = [number for number, _ in found]
    if numbers != list(range(1, len(found) + 1)):
        raise RuntimeError(f"Migration scripts must be numbered 1..n, found {numbers}")
    return found


def schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0])


def init_schema(path: Path) -> None:
    """Bring the database file up to the newest schema this app knows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    scripts = migrations()
    known = len(scripts)
    conn = connect(path)
    try:
        current = schema_version(conn)
        if current < 0 or current > known:
            raise SchemaVersionError(
                f"Database file {path} has schema version {current}, but this app "
                f"knows versions up to {known}. Reset the demo file by deleting it "
                "(it holds synthetic data only)."
            )
        for number, script in scripts[current:]:
            _apply(conn, number, script)
    finally:
        conn.close()


def _apply(conn: sqlite3.Connection, number: int, script: Path) -> None:
    """Run one migration script in its own transaction."""
    try:
        conn.executescript(f"BEGIN;\n{script.read_text()}\nCOMMIT;")
    except sqlite3.Error:
        if conn.in_transaction:
            conn.rollback()
        raise
    if schema_version(conn) != number:
        raise RuntimeError(f"Migration {script.name} must set user_version to {number}")


def get_connection(request: Request) -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request, closed afterwards."""
    conn = connect(request.app.state.database_path)
    try:
        yield conn
    finally:
        conn.close()
