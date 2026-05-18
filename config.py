import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


def connect_to_db():
    user = os.environ["MARIADB_USER"]
    password = os.environ["MARIADB_PASSWORD"]
    host = os.environ.get("MARIADB_HOST", "localhost")
    port = os.environ.get("MARIADB_PORT", "3306")
    database = os.environ["MARIA_DATABASE"]

    return create_engine(
        f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True,
    )


def _connect_from_url_or_parts(prefix, default_database):
    url = os.environ.get(f"{prefix}_URL")
    if url:
        return create_engine(url, pool_pre_ping=True)

    user = os.environ[f"{prefix}_USER"]
    password = os.environ[f"{prefix}_PASSWORD"]
    host = os.environ.get(f"{prefix}_HOST", "localhost")
    port = os.environ.get(f"{prefix}_PORT", "3306")
    database = os.environ.get(f"{prefix}_DATABASE", default_database)

    return create_engine(
        f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True,
    )


def connect_to_dbprod():
    return _connect_from_url_or_parts("DBPROD", "DBPROD")


def connect_to_dbiltr():
    return _connect_from_url_or_parts("DBILTR", "DBILTR")


def get_settings():
    return {
        "date_start": (
            datetime.today()
            - timedelta(days=int(os.environ.get("DATE_START_DAYS", "45")))
        ).date(),
        "reference_datetime": datetime.now()
        - timedelta(days=int(os.environ.get("REFERENCE_HISTORY_DAYS", "365"))),
    }
