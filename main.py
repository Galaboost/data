import logging
import time
from pathlib import Path

from config import connect_to_db, connect_to_dbiltr, connect_to_dbprod, get_settings
from extract import extract_datamart_tables, extract_dbprod_npnpid, read_datamart
from load import load_master, load_param, load_spec, load_vgroup
from transform import (
    build_master_changes,
    build_param_changes,
    build_spec_changes,
    build_vgroup_changes,
)


BASE_DIR = Path(__file__).resolve().parent
VERSION = "v.3.0-python"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "etl_pcm_ref.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def main():
    start = time.perf_counter()
    datamart_engine = None
    dbprod_engine = None
    dbiltr_engine = None
    try:
        settings = get_settings()
        datamart_engine = connect_to_db()
        dbprod_engine = connect_to_dbprod()
        dbiltr_engine = connect_to_dbiltr()
        logger.info("DBILTR_to_datamart_pcm_ref.py - version %s", VERSION)

        prod_npnpid = extract_dbprod_npnpid(settings, dbprod_engine)
        datamart = extract_datamart_tables(datamart_engine)

        created_master, updated_master = build_master_changes(
            settings,
            dbiltr_engine,
            prod_npnpid,
            datamart["ref_master"],
        )
        master_inserted, master_updated = load_master(
            datamart_engine,
            {
                "created_master": created_master,
                "updated_master": updated_master,
            },
        )

        datamart = extract_datamart_tables(datamart_engine)
        new_param, updated_param = build_param_changes(dbiltr_engine, datamart["ref_param"])
        param_inserted, param_updated = load_param(
            datamart_engine,
            {
                "new_param": new_param,
                "updated_param": updated_param,
            },
        )

        datamart = extract_datamart_tables(datamart_engine)
        new_spec, updated_spec = build_spec_changes(
            dbiltr_engine,
            datamart["ref_spec"],
            datamart["ref_npnp"],
            datamart["ref_param_lookup"],
            datamart["ref_spec_lookup"],
        )
        spec_inserted, spec_updated = load_spec(
            datamart_engine,
            {
                "new_spec": new_spec,
                "updated_spec": updated_spec,
            },
        )

        ref_spec_after_load = read_datamart(
            datamart_engine,
            "SELECT * FROM t_pcm_ref_spec",
            "t_pcm_ref_spec after load",
        )
        ref_vgroup = read_datamart(
            datamart_engine,
            "SELECT * FROM t_pcm_ref_vgroup",
            "t_pcm_ref_vgroup after load",
        )
        delete_ids, rebuild_vgroup, new_vgroup, old_triplets = build_vgroup_changes(
            ref_spec_after_load,
            ref_vgroup,
        )
        vgroup_counts = load_vgroup(
            datamart_engine,
            {
                "delete_vgroup_ids": delete_ids,
                "rebuild_vgroup": rebuild_vgroup,
                "new_vgroup": new_vgroup,
                "old_triplet_vgroup": old_triplets,
            },
        )

        elapsed = time.perf_counter() - start
        logger.info("Master inserted=%s updated=%s", master_inserted, master_updated)
        logger.info("Param inserted=%s updated=%s", param_inserted, param_updated)
        logger.info("Spec inserted=%s updated=%s", spec_inserted, spec_updated)
        logger.info("Vgroup counts=%s", vgroup_counts)
        logger.info("RETURNCODE=0")
        logger.info("ETL end in %.2f sec", elapsed)

    except Exception:
        logger.exception("RETURNCODE=2")
        raise
    finally:
        if datamart_engine is not None:
            datamart_engine.dispose()
        if dbprod_engine is not None:
            dbprod_engine.dispose()
        if dbiltr_engine is not None:
            dbiltr_engine.dispose()


if __name__ == "__main__":
    main()
