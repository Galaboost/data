import argparse
import logging
import time
from pathlib import Path

from config import APP_VERSION, connect_to_datamart_db, connect_to_symaro_db
from extract import (
    extract_datamart_reference,
    extract_symaro_data,
)
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


def run_etl(dry_run=False):
    start_time = time.perf_counter()

    logger.info(f"Run ETL Symaro ref oper to datamart - version {APP_VERSION}...")

    symaro_engine = None
    dmp_engine = None

    try:
        symaro_engine = connect_to_symaro_db()
        dmp_engine = connect_to_datamart_db()

        logger.info("successful connected to the DB...")

        logger.info("Extraction des donnees Symaro")
        symaro_data = extract_symaro_data(symaro_engine)
        logger.info(
            "Extraction Symaro terminee: %s",
            ", ".join(f"{name}={len(df)}" for name, df in symaro_data.items()),
        )

        logger.info("Extraction de la reference datamart")
        datamart_reference = extract_datamart_reference(dmp_engine)
        logger.info(f"Reference datamart: {len(datamart_reference)} lignes")

        logger.info("Transformation et calcul du delta")
        symaro_reference = build_symaro_reference(symaro_data)
        created_reference, updated_reference = build_reference_delta(
            datamart_reference,
            symaro_reference
        )

        logger.info(f"Lignes a creer: {len(created_reference)}")
        logger.info(f"Lignes a mettre a jour: {len(updated_reference)}")

        if dry_run:
            logger.info("Dry-run actif: aucune ecriture en base")
            return created_reference, updated_reference

        logger.info("Chargement des nouvelles references")
        load_created_reference(created_reference, dmp_engine)

        logger.info("Mise a jour des references existantes")
        load_updated_reference(updated_reference, dmp_engine)

        elapsed = time.perf_counter() - start_time
        logger.info(f"ETL end in {elapsed:.2f} sec")

        return created_reference, updated_reference

    except Exception:
        logger.exception("Fatal error, stop ETL...")
        raise

    finally:
        if symaro_engine is not None:
            symaro_engine.dispose()

        if dmp_engine is not None:
            dmp_engine.dispose()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Synchronise dmp.t_mes_ref_oper depuis les references Symaro."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calcule les creations/mises a jour sans ecrire dans la base.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    run_etl(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
