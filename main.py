import logging
import time
from pathlib import Path

from config import connect_to_datamart_db, connect_to_symaro_db
from extract import extract_all
from load import load_datamart
from transform import transform_all


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / "etl_symaro_to_datamart.log",
            mode="w",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    start_time = time.perf_counter()

    try:
        symaro_engine = connect_to_symaro_db()
        datamart_engine = connect_to_datamart_db()

        logger.info("successful connected to the DB...")

        data = extract_all(
            symaro_engine,
            datamart_engine
        )

        results = transform_all(data)
        counts = load_datamart(
            datamart_engine,
            results
        )

        elapsed = time.perf_counter() - start_time

        logger.info(f"{counts['route_rows']} route line(s) inserted")
        logger.info(f"{counts['cp_rows']} cp line(s) inserted")
        logger.info(f"ETL end in {elapsed:.2f} sec")

    except Exception:
        logger.exception("Fatal error, stop ETL...")
        raise

    finally:
        if symaro_engine is not None:
            symaro_engine.dispose()

        if datamart_engine is not None:
            datamart_engine.dispose()


if __name__ == "__main__":
    main()
