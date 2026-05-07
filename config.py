from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, create_engine


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class DatabaseConfig:
    dialect: str
    user: str
    password: str
    database: str
    host: str
    port: int

    def url(self) -> str:
        return (
            f"{self.dialect}://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


def load_env_file(path: Path | None = None) -> None:
    env_path = path or BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def getenv_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def get_symaro_config() -> DatabaseConfig:
    load_env_file()
    return DatabaseConfig(
        dialect=os.environ.get("SYMARO_DIALECT", "mysql+pymysql"),
        user=os.environ.get("SYMARO_USER", "appdatamart"),
        password=os.environ.get("SYMARO_PASSWORD", "appdatamart01"),
        database=os.environ.get("SYMARO_DATABASE", "symaro"),
        host=os.environ.get("SYMARO_HOST", "symarodb"),
        port=getenv_int("SYMARO_PORT", 3306),
    )


def get_dmp_config() -> DatabaseConfig:
    load_env_file()
    return DatabaseConfig(
        dialect=os.environ.get("DMP_DIALECT", "mariadb+mariadbconnector"),
        user=os.environ.get("DMP_USER", "appdatamart"),
        password=os.environ.get("DMP_PASSWORD", "appdatamart1"),
        database=os.environ.get("DMP_DATABASE", "dmp"),
        host=os.environ.get("DMP_HOST", "maxscale"),
        port=getenv_int("DMP_PORT", 4306),
    )


def build_engine(config: DatabaseConfig) -> Engine:
    return create_engine(config.url())


def get_symaro_engine() -> Engine:
    return build_engine(get_symaro_config())


def get_dmp_engine() -> Engine:
    return build_engine(get_dmp_config())
