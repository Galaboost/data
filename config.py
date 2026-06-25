import os

from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


def connect_to_reftool():
    url = os.environ.get("REFTOOL_URL")
    if url:
        return create_engine(url, pool_pre_ping=True)

    user = os.environ.get("REFTOOL_USER", "reftool_user")
    password = os.environ.get("REFTOOL_PASSWORD", "reftool_user")
    host = os.environ.get("REFTOOL_HOST", "reftooldb-dev.altissemiconductor.com")
    port = os.environ.get("REFTOOL_PORT", "3306")
    database = os.environ.get("REFTOOL_DATABASE", "reftool")
    return create_engine(
        f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True,
    )


def connect_to_dmp():
    url = os.environ.get("REFTOOL_DMP_URL") or os.environ.get("DMP_URL")
    if url:
        return create_engine(url, pool_pre_ping=True)

    user = os.environ.get("REFTOOL_DMP_USER", "appdatamart")
    password = os.environ.get("REFTOOL_DMP_PASSWORD", "appdatamart1")
    host = os.environ.get("REFTOOL_DMP_HOST", "maxscale")
    port = os.environ.get("REFTOOL_DMP_PORT", "4306")
    database = os.environ.get("REFTOOL_DMP_DATABASE", "dmp")
    return create_engine(
        f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True,
    )
