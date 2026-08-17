import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path

from config import (
    connect_to_datamart_db,
    connect_to_dbprod_db,
)
from extract import (
    extract_lot_measurements,
    extract_swt_profiles,
    extract_wafer_measurements,
)
from load import (
    allgood_wafer_path,
    lot_archive_path,
    read_archive_csv,
    wafer_archive_path,
    write_archive_csv,
)
from transform import (
    ACTIVE_TECHNOS,
    build_allgood_wafer,
    combine_measurements,
    format_identifier,
    get_archive_directory,
    get_pmax,
    merge_archive,
    prepare_profiles,
    transform_swt_measurements,
)

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "SWT_TO_EDA_CSV.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def get_swt_date_window():
    days = int(os.environ.get("SWT_LOOKBACK_DAYS", "30"))
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return start_date.isoformat(), end_date.isoformat()


def get_swt_root_directory():
    # Production output:
    # /home/auemura@xfab.ads/share/EDASHARE/EDA_PUBLIC/CARAC
    return os.environ.get(
        "SWT_ROOT_DIRECTORY",
        BASE_DIR,
    )


def get_swt_active_technos(default_technos):
    raw = os.environ.get("SWT_ACTIVE_TECHNOS")
    if not raw:
        return default_technos
    return tuple(value.strip() for value in raw.split(",") if value.strip())


def process_profile(profile, dbprod_engine, root_directory, start_date, end_date):
    techno = str(profile["techno"])
    npnpid = format_identifier(profile["npnpid"])
    version = format_identifier(profile["version"])
    archive_directory = get_archive_directory(techno, root_directory)
    pmax = get_pmax(techno)

    logger.info(
        "Start SWT profile techno=%s, npnpid=%s, version=%s",
        techno,
        npnpid,
        version,
    )

    lot_parametric, lot_yield = extract_lot_measurements(
        dbprod_engine, npnpid, version, start_date, end_date
    )
    lot_fresh = transform_swt_measurements(
        combine_measurements(lot_parametric, lot_yield),
        pmax=pmax,
        id_columns=["NLOCFAB", "DDTEST", "NPNPID", "VERSION"],
    )
    lot_path = lot_archive_path(archive_directory, npnpid)
    existing_lot_archive = read_archive_csv(lot_path)
    lot_archive = merge_archive(existing_lot_archive, lot_fresh, ["NLOCFAB"])
    if not lot_archive.empty:
        write_archive_csv(lot_archive, lot_path)
    else:
        logger.info("Skip lot CSV for npnpid=%s: no fresh or archived row", npnpid)

    wafer_parametric, wafer_yield = extract_wafer_measurements(
        dbprod_engine, npnpid, version, start_date, end_date
    )
    wafer_fresh = transform_swt_measurements(
        combine_measurements(wafer_parametric, wafer_yield),
        pmax=pmax,
        id_columns=["NLOCFAB", "NTRANCH", "DDTEST", "NPNPID", "VERSION"],
    )
    wafer_path = wafer_archive_path(archive_directory, npnpid)
    existing_wafer_archive = read_archive_csv(wafer_path)
    wafer_archive = merge_archive(existing_wafer_archive, wafer_fresh, ["NLOCFAB", "NTRANCH"])
    if not wafer_archive.empty:
        write_archive_csv(wafer_archive, wafer_path)
    else:
        logger.info("Skip wafer CSV for npnpid=%s: no fresh or archived row", npnpid)

    allgood_rows = 0
    if techno == "T18SO" and not wafer_archive.empty:
        allgood = build_allgood_wafer(wafer_archive)
        write_archive_csv(allgood, allgood_wafer_path(archive_directory, npnpid))
        allgood_rows = len(allgood)

    return {
        "techno": techno,
        "npnpid": npnpid,
        "version": version,
        "lot_rows": len(lot_archive),
        "wafer_rows": len(wafer_archive),
        "allgood_rows": allgood_rows,
    }


def run_etl():
    started = time.perf_counter()
    start_date, end_date = get_swt_date_window()
    root_directory = get_swt_root_directory()
    active_technos = get_swt_active_technos(ACTIVE_TECHNOS)
    results = []

    logger.info("START SWT ETL")
    logger.info("Date window: %s to %s", start_date, end_date)
    logger.info("Archive root: %s", root_directory)

    dmp_engine = connect_to_datamart_db()
    dbprod_engine = connect_to_dbprod_db()
    try:
        profiles = prepare_profiles(extract_swt_profiles(dmp_engine), active_technos)
        logger.info("%s SWT profile(s) selected", len(profiles))

        for _, profile in profiles.iterrows():
            result = process_profile(profile, dbprod_engine, root_directory, start_date, end_date)
            if result:
                results.append(result)

        logger.info("END SWT ETL in %.2f sec", time.perf_counter() - started)
        return results
    finally:
        dmp_engine.dispose()
        dbprod_engine.dispose()


if __name__ == "__main__":
    run_etl()
