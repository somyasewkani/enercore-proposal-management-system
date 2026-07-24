"""Database module for Enercore AI Solar Proposal Generator."""

from pathlib import Path
import os

# Project root schema path
SCHEMA_PATH = Path(__file__).parent.parent.parent / "database" / "schema.sql"


def get_schema_sql() -> str:
    """Read and return the schema SQL from the root database/schema.sql file."""
    schema_file = SCHEMA_PATH
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_file}")
    return schema_file.read_text(encoding="utf-8")


def init_database(connection) -> None:
    """Initialize database tables using the schema.sql file."""
    schema_sql = get_schema_sql()
    with connection.cursor() as cur:
        cur.execute(schema_sql)
    connection.commit()


__all__ = ["SCHEMA_PATH", "get_schema_sql", "init_database"]