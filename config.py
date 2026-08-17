import os

from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


def connect_to_datamart_db():
    user = os.environ.get("DATAMART_USER", "appdatamart")
    password = os.environ["DATAMART_PASSWORD"]
    host = os.environ.get("DATAMART_HOST", "maxscale")
    port = os.environ.get("DATAMART_PORT", "4306")
    database = os.environ.get("DATAMART_DATABASE", "dmp")

    return create_engine(
        f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True,
    )


def connect_to_dbprod_db():
    user = os.environ["DBPROD_USER"]
    password = os.environ["DBPROD_PASSWORD"]
    host = os.environ.get("DBPROD_HOST", "DBPROD")
    port = os.environ.get("DBPROD_PORT", "3306")
    database = os.environ.get("DBPROD_DATABASE", "DBPROD")

    return create_engine(
        f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True,
    )
