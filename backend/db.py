"""Database connection only; schema.sql owns table creation in Slice 0."""
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


def create_database_engine():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Set DATABASE_URL before starting the backend; see README.md.")
    url = make_url(database_url)
    if url.drivername != "postgresql+psycopg":
        raise RuntimeError("DATABASE_URL must use postgresql+psycopg://.")
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


engine = create_database_engine()
