import logging
from pathlib import Path

import pandas as pd

from config import get_pmax
from extract import extract_lot_data, extract_wafer_data
from transform import (
    merge_with_archive,
    select_allgood_wafer,
    transform_lot_data,
    transform_wafer_data,
)


logger = logging.getLogger(__name__)


def read_archive(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    logger.info("Read archive %s", path)
    return pd.read_csv(path)


def write_archive(path: Path, df: pd.DataFrame) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Wrote %s row(s) to %s", len(df), path)
    return len(df)


def lot_archive_path(directory: Path, npnpid: str) -> Path:
    return directory / f"db{npnpid}l.csv"


def wafer_archive_path(directory: Path, npnpid: str) -> Path:
    return directory / f"db{npnpid}w.csv"


def allgood_archive_path(directory: Path, npnpid: str) -> Path:
    return directory / f"db{npnpid}wb.csv"


def update_lot_archive(dbprod_connection, directory: Path, profile, nparams, settings) -> pd.DataFrame:
    raw = extract_lot_data(
        dbprod_connection,
        profile.npnpid,
        profile.version,
        nparams,
        settings.start_date,
        settings.end_date,
    )
    transformed = transform_lot_data(raw, get_pmax(profile.techno))
    path = lot_archive_path(directory, profile.npnpid)
    merged, new_lots = merge_with_archive(
        read_archive(path),
        transformed,
        group_columns=["NLOCFAB"],
        sort_columns=["DDTEST", "NLOCFAB"],
    )
    logger.info("Lot archive %s: %s new lot(s)", profile.npnpid, new_lots)
    if not merged.empty:
        write_archive(path, merged)
    return merged


def update_wafer_archive(dbprod_connection, directory: Path, profile, nparams, settings) -> pd.DataFrame:
    raw = extract_wafer_data(
        dbprod_connection,
        profile.npnpid,
        profile.version,
        nparams,
        settings.start_date,
        settings.end_date,
    )
    transformed = transform_wafer_data(raw, get_pmax(profile.techno))
    path = wafer_archive_path(directory, profile.npnpid)
    merged, new_lots = merge_with_archive(
        read_archive(path),
        transformed,
        group_columns=["NLOCFAB", "NTRANCH"],
        sort_columns=["DDTEST", "NLOCFAB", "NTRANCH"],
    )
    logger.info("Wafer archive %s: %s new lot(s)", profile.npnpid, new_lots)
    if not merged.empty:
        write_archive(path, merged)
    return merged


def update_allgood_archive(directory: Path, profile, wafer_archive: pd.DataFrame) -> int:
    if profile.techno != "T18SO":
        return 0
    allgood = select_allgood_wafer(wafer_archive)
    if allgood.empty:
        logger.info("No AllGood wafer archive for %s", profile.npnpid)
        return 0
    return write_archive(allgood_archive_path(directory, profile.npnpid), allgood)
