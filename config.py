import os

from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


SEND_TO_DB_INSERT = "yes"
SEND_TO_DB_UPDATE = "update"

MASKSET_ALIASES = {"F62494A": "62494A"}

DBMAPS_MAP_TYPE = "e"

EMAP_COLUMNS = [
    "sapn",
    "maskset_name",
    "device_id",
    "version",
    "filename",
    "effective_fra_datetime",
    "ret_x_size",
    "ret_y_size",
    "ret_y_vs_x_ratio",
    "ret_x_max",
    "ret_y_max",
    "die_qty",
    "die_x_size",
    "die_y_size",
    "die_y_vs_x_ratio",
    "die_x_max",
    "die_y_max",
    "swt_die_x_offset",
    "swt_die_y_offset",
]

RET_COLUMNS = [
    "emap_id",
    "ret_x",
    "ret_y",
    "ret_type",
    "test_ret_type",
    "center_mm_distance",
]

DIE_COLUMNS = [
    "emap_id",
    "ret_id",
    "die_x",
    "die_y",
    "die_x_ret_position",
    "die_y_ret_position",
    "die_type",
]


def get_send_to_db() -> str:
    return os.environ.get("DBMAPS_SEND_TO_DB", SEND_TO_DB_INSERT).strip().lower()


def get_device_limit() -> int:
    return int(os.environ.get("DBMAPS_DEVICE_LIMIT", "10"))


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _engine_from_env(prefix: str):
    url = os.environ.get(f"{prefix}_URL")
    if url:
        return create_engine(url, pool_pre_ping=True)

    user = _required_env(f"{prefix}_USER")
    password = _required_env(f"{prefix}_PASSWORD")
    host = _required_env(f"{prefix}_HOST")
    port = _required_env(f"{prefix}_PORT")
    database = _required_env(f"{prefix}_DATABASE")
    driver = os.environ.get(f"{prefix}_DRIVER", "mysqlconnector")
    return create_engine(
        f"mysql+{driver}://{user}:{password}@{host}:{port}/{database}",
        pool_pre_ping=True,
    )


def connect_to_dmp():
    return _engine_from_env("DMP")


def connect_to_dbmaps():
    return _engine_from_env("DBMAPS")
