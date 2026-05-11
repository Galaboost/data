import os

from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()

APP_VERSION = os.environ.get("APP_VERSION", "1.0")


def connect_to_symaro_db():
    user = os.environ.get("SYMARO_USER", "appdatamart")
    password = os.environ.get("SYMARO_PASSWORD", "appdatamart01")
    host = os.environ.get("SYMARO_HOST", "symarodb")
    port = os.environ.get("SYMARO_PORT", "3306")
    database = os.environ.get("SYMARO_DATABASE", "symaro")
    dialect = os.environ.get("SYMARO_DIALECT", "mysql+mysqlconnector")

    return create_engine(
        f"{dialect}://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True
    )


def connect_to_datamart_db():
    user = os.environ.get("DMP_USER", "appdatamart")
    password = os.environ.get("DMP_PASSWORD", "appdatamart1")
    host = os.environ.get("DMP_HOST", "maxscale")
    port = os.environ.get("DMP_PORT", "4306")
    database = os.environ.get("DMP_DATABASE", "dmp")
    dialect = os.environ.get("DMP_DIALECT", "mysql+mysqlconnector")

    return create_engine(
        f"{dialect}://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True
    )
