import sqlalchemy

DATABASE_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def create_database_engine(path: str) -> sqlalchemy.engine.Engine:
    """
    Creates an SQLAlchemy database engine for the SQLite database
    at the given path.
    """
    return sqlalchemy.create_engine('sqlite:///' + path)
