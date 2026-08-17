import logging
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)


def read_archive_csv(path):
    path = Path(path)
    if not path.exists():
        return None
    logger.info("Read archive %s", path)
    return pd.read_csv(path)


def write_archive_csv(df, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Wrote %s row(s) to %s", len(df), path)


def lot_archive_path(directory, npnpid):
    return Path(directory) / f"db{npnpid}l.csv"


def wafer_archive_path(directory, npnpid):
    return Path(directory) / f"db{npnpid}w.csv"


def allgood_wafer_path(directory, npnpid):
    return Path(directory) / f"db{npnpid}wb.csv"
