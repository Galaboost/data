import logging
import time

from config import (
    archive_directory,
    close_connection,
    connect_to_dbprod,
    connect_to_dmp,
    get_nparam,
    get_settings,
)
from extract import extract_available_nparams, extract_swt_profiles
from load import update_allgood_archive, update_lot_archive, update_wafer_archive


VERSION = "fra.eda_csv-python-v1"
logger = logging.getLogger(__name__)


def main():
    start = time.perf_counter()
    settings = get_settings()
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(settings.log_dir / "eda_csv.log", mode="w", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    dbprod_connection = None
    dmp_connection = None
    try:
        logger.info("START script eda_csv Python - %s", VERSION)
        logger.info("Date window: %s to %s", settings.start_date, settings.end_date)

        dbprod_connection = connect_to_dbprod()
        dmp_connection = connect_to_dmp()

        profiles = extract_swt_profiles(dmp_connection)
        profiles = profiles[profiles["techno"].isin(settings.active_technos)].reset_index(drop=True)
        logger.info("Number of active profile rows: %s", len(profiles))

        if profiles.empty:
            raise RuntimeError("No active SWT profile found in t_profile_maps_master")

        for index, profile in enumerate(profiles.itertuples(index=False), start=1):
            logger.info(
                "%s/%s start techno=%s npnpid=%s version=%s",
                index,
                len(profiles),
                profile.techno,
                profile.npnpid,
                profile.version,
            )

            directory = archive_directory(settings, profile.techno)
            nparams = get_nparam(profile.techno)
            if not nparams:
                nparams = extract_available_nparams(dbprod_connection, profile.npnpid, profile.version)
            if not nparams:
                logger.info("No NPARAM for techno=%s npnpid=%s", profile.techno, profile.npnpid)
                continue

            update_lot_archive(dbprod_connection, directory, profile, nparams, settings)
            wafer_archive = update_wafer_archive(dbprod_connection, directory, profile, nparams, settings)
            update_allgood_archive(directory, profile, wafer_archive)
            logger.info("End profile npnpid=%s", profile.npnpid)

        logger.info("RETURNCODE=0")
        logger.info("END script in %.2f sec", time.perf_counter() - start)
    except Exception:
        logger.exception("RETURNCODE=2")
        raise
    finally:
        close_connection(dbprod_connection)
        close_connection(dmp_connection)


if __name__ == "__main__":
    main()
