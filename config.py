import os

from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


def connect_to_dmp():
    url = os.environ.get("DMP_URL")
    if url:
        return create_engine(url, pool_pre_ping=True)

    user = os.environ["DMP_USER"]
    password = os.environ["DMP_PASSWORD"]
    host = os.environ.get("DMP_HOST", "localhost")
    port = os.environ.get("DMP_PORT", "4306")
    database = os.environ.get("DMP_DATABASE", "dmp")
    return create_engine(
        f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True,
    )


def connect_to_dbtrade():
    try:
        import ibm_db_dbi
    except ImportError as exc:
        raise RuntimeError(
            "DBTRADE requires the ibm-db package and its IBM DB2 runtime DLLs."
        ) from exc

    connection_string = os.environ.get("DBTRADE_CONNECTION_STRING")
    if connection_string:
        return ibm_db_dbi.connect(connection_string, "", "")

    database = os.environ["DBTRADE_DATABASE"]
    host = os.environ["DBTRADE_HOST"]
    port = os.environ.get("DBTRADE_PORT", "50000")
    user = os.environ["DBTRADE_USER"]
    password = os.environ["DBTRADE_PASSWORD"]
    conn = (
        f"DATABASE={database};"
        f"HOSTNAME={host};"
        f"PORT={port};"
        "PROTOCOL=TCPIP;"
        f"UID={user};"
        f"PWD={password};"
    )
    return ibm_db_dbi.connect(conn, "", "")
