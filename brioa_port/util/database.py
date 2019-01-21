import sqlalchemy

from pathlib import Path

DATABASE_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

def create_database_engine(path: str) -> sqlalchemy.engine.Engine:
    return sqlalchemy.create_engine('sqlite:///' + path)
