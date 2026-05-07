from __future__ import annotations

import argparse
import logging

import pandas as pd

from extract import (
    extract_datamart_reference,
    extract_symaro_data,
    get_dmp_engine,
    get_symaro_engine,
)
from load import load_created_reference, load_updated_reference
from transform import build_reference_delta, build_symaro_reference


LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_etl(*, dry_run: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    LOGGER.info("Demarrage ETL Symaro -> Datamart")

    symaro_engine = get_symaro_engine()
    dmp_engine = get_dmp_engine()

    LOGGER.info("Extraction des donnees Symaro")
    symaro_data = extract_symaro_data(symaro_engine)
    LOGGER.info(
        "Extraction Symaro terminee: %s",
        ", ".join(f"{name}={len(df)}" for name, df in symaro_data.items()),
    )

    LOGGER.info("Extraction de la reference datamart")
    datamart_reference = extract_datamart_reference(dmp_engine)
    LOGGER.info("Reference datamart: %s lignes", len(datamart_reference))

    LOGGER.info("Transformation et calcul du delta")
    symaro_reference = build_symaro_reference(symaro_data)
    created_reference, updated_reference = build_reference_delta(
        datamart_reference, symaro_reference
    )
    LOGGER.info("Lignes a creer: %s", len(created_reference))
    LOGGER.info("Lignes a mettre a jour: %s", len(updated_reference))

    if dry_run:
        LOGGER.info("Dry-run actif: aucune ecriture en base")
        return created_reference, updated_reference

    LOGGER.info("Chargement des nouvelles references")
    load_created_reference(created_reference, dmp_engine)

    LOGGER.info("Mise a jour des references existantes")
    load_updated_reference(updated_reference, dmp_engine)

    LOGGER.info("ETL termine")
    return created_reference, updated_reference


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronise dmp.t_mes_ref_oper depuis les references Symaro."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calcule les creations/mises a jour sans ecrire dans la base.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    configure_logging()
    args = parse_args()
    run_etl(dry_run=args.dry_run)
