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


def get_dbprod_config():
    return {
        "dsn": os.environ.get("DBPROD_DSN", "DBPROD"),
        "user": os.environ["DBPROD_USER"],
        "password": os.environ["DBPROD_PASSWORD"],
    }


def get_dbiltr_config():
    return {
        "dsn": os.environ.get("DBILTR_DSN", os.environ.get("DBISIS_DSN", "DBILTR")),
        "user": os.environ["DBILTR_USER"],
        "password": os.environ["DBILTR_PASSWORD"],
    }


def get_settings():
    return {
        "dbprod": get_dbprod_config(),
        "dbiltr": get_dbiltr_config(),
        "date_start": (
            datetime.today()
            - timedelta(days=int(os.environ.get("DATE_START_DAYS", "45")))
        ).date(),
        "reference_datetime": datetime.now()
        - timedelta(days=int(os.environ.get("REFERENCE_HISTORY_DAYS", "365"))),
    }
