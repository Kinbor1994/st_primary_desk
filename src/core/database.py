"""
This module handles the database connection for the School Desk application.

It sets up the SQLModel engine for SQLite and provides a function to create the
database and tables.
"""

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

import logging
from alembic import command
from alembic.config import Config

# Define paths relative to this file's location (src/core).
# CORE_DIR will be the absolute path to the 'src/core' directory.
CORE_DIR = Path(__file__).parent.resolve()
DATABASE_FILE = "p_desk.db"
DATABASE_PATH = CORE_DIR / DATABASE_FILE

# The database file will be named "school_desk.db" and located in the 'src/core' directory.
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# The engine is the entry point to the database.
# `echo=True` is useful for debugging as it logs all SQL statements.
# `connect_args` is needed for SQLite to ensure thread safety.
engine = create_engine(
    DATABASE_URL, echo=True, connect_args={"check_same_thread": False}
)


def create_db_and_tables():
    """
    Initializes the database by applying all Alembic migrations.

    Instead of creating tables directly from the models, this function
    runs 'alembic upgrade head' to ensure the schema is up-to-date
    with the latest migration script.
    """
    # alembic.ini is located in the project root, two levels up from this file (src/core).
    project_root = CORE_DIR.parent.parent
    ini_path = project_root / "alembic.ini"

    # If there are no migration scripts, fall back to creating tables
    # directly from the SQLModel metadata. This helps first-time setups
    # or environments where Alembic revisions weren't generated yet.
    versions_dir = project_root / "alembic" / "versions"
    if not versions_dir.exists() or not any(versions_dir.iterdir()):
        logging.info("No Alembic migrations found, creating tables from models.")
        SQLModel.metadata.create_all(engine)
        return

    alembic_cfg = Config(str(ini_path))
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as exc:
        logging.exception("Alembic upgrade failed, falling back to create_all: %s", exc)
        SQLModel.metadata.create_all(engine)


def get_session():
    """
    Dependency function to get a new database session.

    This will be used by services to interact with the database.
    """
    with Session(engine) as session:
        yield session
