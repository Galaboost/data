import logging
import os
import time
from pathlib import Path

from config import connect_to_dbtrade, connect_to_dmp
from extract import extract_detected_reference_data, extract_reference_parameters
from load import load_reference_payload
from transform import add_swt_ref_ids, build_new_references, build_reference_payload


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / "DBTRADEref_to_datamart_swt_ref.log",
            mode="w",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_etl():
    start_time = time.perf_counter()

    try:
        dbtrade_connection = connect_to_dbtrade()
        dmp_engine = connect_to_dmp()
        dmp_database = os.environ.get("DMP_DATABASE", "dmp")
        lookback_days = int(os.environ.get("DBTRADE_LOOKBACK_DAYS", "20"))

        t0 = time.perf_counter()
        source_data = extract_detected_reference_data(
            dbtrade_connection,
            dmp_engine,
            lookback_days
        )
        logger.info(f"Extract done in {time.perf_counter() - t0:.2f} sec")

        t0 = time.perf_counter()
        new_references = build_new_references(source_data)
        new_references = add_swt_ref_ids(new_references, source_data["ref_master"])
        logger.info(f"Transform done in {time.perf_counter() - t0:.2f} sec")
        logger.info(f"{len(new_references)} reference(s) to insert")

        t0 = time.perf_counter()
        for reference in new_references.itertuples(index=False):
            parameter_data = extract_reference_parameters(
                dbtrade_connection,
                dmp_engine,
                dmp_database,
                reference
            )
            payload = build_reference_payload(reference, parameter_data)
            load_reference_payload(payload, dmp_engine)

        logger.info(f"Load done in {time.perf_counter() - t0:.2f} sec")
        logger.info(f"End ETL in {time.perf_counter() - start_time:.2f} sec")

        return new_references

    except Exception:
        logger.exception("Fatal error")
        raise
    finally:
        if "dbtrade_connection" in locals():
            dbtrade_connection.close()
        if "dmp_engine" in locals():
            dmp_engine.dispose()


if __name__ == "__main__":
    run_etl()
