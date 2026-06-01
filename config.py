import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


ACTIVE_TECHNOS = ("AH018", "C11N", "XH018", "XR013", "XT011", "XT018")

TECHNO_DIRECTORIES = {
    "AH018": "FWT_AH18",
    "C10N": "FWT_C10",
    "C11N": "FWT_C11",
    "T18AL": "FWT_SOI",
    "T18B": "FWT_T18B",
    "T18RF": "FWT_T18RF",
    "T18SO": "FWT_SOI",
    "XH018": "FWT_XH018",
    "XP018": "FWT_XP018",
    "XR013": "FWT_XR013",
    "XT011": "FWT_XT011",
    "XT018": "FWT_XT018",
}


@dataclass(frozen=True)
class Settings:
    project_dir: Path
    archive_root: Path
    log_dir: Path
    start_date: date
    end_date: date
    active_technos: tuple[str, ...]


def _int_env(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def get_settings() -> Settings:
    project_dir = Path(__file__).resolve().parent
    archive_root = Path(
        os.environ.get(
            "EDA_PUBLIC_ROOT",
            "/home/auemura@xfab.ads/share/EDASHARE/EDA_PUBLIC/CARAC",
        )
    )
    log_dir = Path(os.environ.get("LOG_DIR", project_dir / "logs"))
    end_date = date.today()
    start_date = end_date - timedelta(days=_int_env("UPDATE_WINDOW_DAYS", 30))
    active = tuple(
        item.strip()
        for item in os.environ.get("ACTIVE_TECHNOS", ",".join(ACTIVE_TECHNOS)).split(",")
        if item.strip()
    )
    return Settings(
        project_dir=project_dir,
        archive_root=archive_root,
        log_dir=log_dir,
        start_date=start_date,
        end_date=end_date,
        active_technos=active,
    )


def connect_to_dbprod():
    try:
        import ibm_db_dbi
    except ImportError as exc:
        raise RuntimeError(
            "DBPROD requires the ibm-db package and its IBM DB2 runtime DLLs. "
            "Install ibm-db and verify the IBM DB2 client runtime is loadable."
        ) from exc

    connection_string = os.environ.get("DBPROD_CONNECTION_STRING")
    if connection_string:
        return ibm_db_dbi.connect(connection_string, "", "")

    database = os.environ["DBPROD_DATABASE"]
    host = os.environ["DBPROD_HOST"]
    port = os.environ.get("DBPROD_PORT", "50000")
    user = os.environ["DBPROD_USER"]
    password = os.environ["DBPROD_PASSWORD"]
    conn = (
        f"DATABASE={database};"
        f"HOSTNAME={host};"
        f"PORT={port};"
        "PROTOCOL=TCPIP;"
        f"UID={user};"
        f"PWD={password};"
    )
    return ibm_db_dbi.connect(conn, "", "")


def connect_to_dmp():
    url = os.environ.get("DMP_URL")
    if url:
        return create_engine(url, pool_pre_ping=True)

    user = os.environ["DMP_USER"]
    password = os.environ["DMP_PASSWORD"]
    host = os.environ.get("DMP_HOST", "localhost")
    port = os.environ.get("DMP_PORT", "3306")
    database = os.environ.get("DMP_DATABASE", "dmp")
    return create_engine(
        f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True,
    )


def close_connection(connection):
    if connection is None:
        return
    if hasattr(connection, "dispose"):
        connection.dispose()
        return
    connection.close()


def archive_directory(settings: Settings, techno: str) -> Path:
    if techno not in TECHNO_DIRECTORIES:
        raise ValueError(f"Technology directory is not defined: {techno}")
    return settings.archive_root / TECHNO_DIRECTORIES[techno]


def get_pmax(techno: str) -> int:
    return 10000 if techno == "T18SO" else 12000


def get_nparam(techno: str) -> list[int]:
    base = [10691, 10695, 10696, 10697, 10698, 10699]
    broad = list(range(10000, 10061))

    if techno == "T18RF":
        return [
            10691,
            10692,
            10693,
            10595,
            10596,
            10597,
            10598,
            10599,
            10000,
            10001,
            10002,
            10003,
            10004,
            10005,
            10006,
            10007,
            10008,
            10009,
            10015,
            10017,
            10026,
            10027,
            10028,
            10029,
            10030,
            10037,
            10063,
            10064,
            10072,
            10074,
            10080,
            10327,
        ]
    if techno in ("XH018", "XT018"):
        return base + broad
    if techno == "AH018":
        return base + list(range(10001, 10071)) + [10099]
    if techno == "XP018":
        return base + [
            10001,
            10002,
            10003,
            10004,
            10005,
            10006,
            10007,
            10008,
            10009,
            10010,
            10011,
            10012,
            10013,
            10015,
            10016,
            10017,
            10018,
            10019,
            10021,
            10022,
            10025,
            10026,
            10028,
            10029,
            10032,
            10033,
            10035,
            10036,
            10057,
            10058,
            10060,
            10062,
            10063,
            10064,
            10099,
        ]
    if techno == "XR013":
        return base + [10001, 10002, 10003, 10004, 10005, 10006, 10007, 10008, 10009, 10010, 10032, 10035]
    return base + broad[:51]
