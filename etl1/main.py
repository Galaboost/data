import logging
import time
from pathlib import Path

from config import connect_to_datamart_db, connect_to_symaro_db
from extract import extract_datamart_reference, extract_symaro_data
from load import load_created_reference, load_updated_reference
from transform import build_reference_delta, build_symaro_reference


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / "etl_symaro_ref_oper.log",
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
        symaro_engine = connect_to_symaro_db()
        dmp_engine = connect_to_datamart_db()

        symaro_data = extract_symaro_data(symaro_engine)
        datamart_reference = extract_datamart_reference(dmp_engine)

        symaro_reference = build_symaro_reference(symaro_data)

        created_reference, updated_reference = build_reference_delta(
            datamart_reference,
            symaro_reference
        )

        logger.info(
            f"Delta: {len(created_reference)} insert(s), "
            f"{len(updated_reference)} update(s)"
        )

        load_created_reference(created_reference, dmp_engine)
        load_updated_reference(updated_reference, dmp_engine)

        elapsed = time.perf_counter() - start_time
        logger.info(f"End ETL in {elapsed:.2f} sec")

        return created_reference, updated_reference

    except Exception:
        logger.exception("Fatal error")
        raise

    finally:
        if symaro_engine is not None:
            symaro_engine.dispose()

        if dmp_engine is not None:
            dmp_engine.dispose()


if __name__ == "__main__":
    run_etl()