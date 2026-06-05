import logging
import os
import time
from pathlib import Path

from config import connect_to_dbtrade, connect_to_dmp
from extract import (
    extract_analog_limits,
    extract_analog_parameters,
    extract_histo_master_refs,
    extract_max_ref_param_id,
    extract_recent_index_refs,
    extract_ref_master,
    extract_ref_params,
    extract_yield_limits,
    extract_yield_parameters,
)
from load import load_ref_analog, load_ref_master, load_ref_param, load_ref_yield
from transform import (
    build_analog_rows,
    build_ref_master_row,
    build_ref_param_rows,
    build_yield_rows,
    combine_detected_refs,
    find_new_refs,
    max_swt_ref_id,
    transform_histo_refs,
    transform_index_refs,
)


logger = logging.getLogger(__name__)
VERSION = "v.2.7-python"


def close_connection(connection):
    if connection is None:
        return
    if hasattr(connection, "dispose"):
        connection.dispose()
        return
    connection.close()


def configure_logging():
    project_dir = Path(__file__).resolve().parent
    log_dir = Path(os.environ.get("LOG_DIR", project_dir / "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(
                log_dir / "DBTRADEref_to_datamart_swt_ref.py.log",
                mode="w",
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
    )


def load_reference(dbtrade_connection, dmp_engine, dmp_database: str, ref_row, swt_ref_id: int):
    npnp_id = int(ref_row.npnp_id)
    version = int(ref_row.version)
    product_code = str(ref_row.product_code)

    logger.info(
        "Start npnp_id=%s version=%s product_code=%s swt_ref_id=%s",
        npnp_id,
        version,
        product_code,
        swt_ref_id,
    )

    load_ref_master(dmp_engine, build_ref_master_row(ref_row, swt_ref_id))
    logger.info("--End update dmp t_swt_ref_master >>")

    last_param_id = extract_max_ref_param_id(dmp_engine, dmp_database)
    yield_params = extract_yield_parameters(dbtrade_connection, npnp_id, version, product_code)
    analog_params = extract_analog_parameters(dbtrade_connection, npnp_id, version, product_code)
    ref_param_rows = build_ref_param_rows(yield_params, analog_params, swt_ref_id, last_param_id)
    load_ref_param(dmp_engine, ref_param_rows)
    logger.info("--End update dmp t_swt_ref_param >>")

    ref_params = extract_ref_params(dmp_engine, dmp_database, swt_ref_id)

    yield_limits = extract_yield_limits(dbtrade_connection, npnp_id, version, product_code)
    yield_rows = build_yield_rows(ref_params, yield_limits)
    load_ref_yield(dmp_engine, yield_rows)
    logger.info("--End update dmp t_swt_ref_yield >>")

    analog_limits = extract_analog_limits(dbtrade_connection, npnp_id, version, product_code)
    analog_rows = build_analog_rows(ref_params, analog_limits)
    load_ref_analog(dmp_engine, analog_rows)
    logger.info("--End update dmp t_swt_ref_analog >>")


def main():
    start = time.perf_counter()
    configure_logging()
    dmp_database = os.environ.get("DMP_DATABASE", "dmp")
    lookback_days = int(os.environ.get("DBTRADE_LOOKBACK_DAYS", "20"))

    dbtrade_connection = None
    dmp_engine = None
    try:
        logger.info("dm_t_swt_ref_new.py %s - new search of reference to load", VERSION)
        dbtrade_connection = connect_to_dbtrade()
        dmp_engine = connect_to_dmp()

        index_refs = transform_index_refs(
            extract_recent_index_refs(dbtrade_connection, lookback_days)
        )
        histo_refs = transform_histo_refs(extract_histo_master_refs(dbtrade_connection))
        detected_refs = combine_detected_refs(index_refs, histo_refs)

        ref_master = extract_ref_master(dmp_engine)
        new_refs = find_new_refs(detected_refs, ref_master)
        logger.info("Detection of new ref: %s", len(new_refs))

        if new_refs.empty:
            logger.info("------------------------- End -------------------------")
            return

        logger.info("<<<<---- start of reference update ----")
        last_ref_id = max_swt_ref_id(ref_master)
        for k, ref_row in enumerate(new_refs.itertuples(index=False), start=1):
            swt_ref_id = last_ref_id + k
            logger.info(
                "%s, npnp_id:%s - version:%s - product_code:%s",
                k,
                ref_row.npnp_id,
                ref_row.version,
                ref_row.product_code,
            )
            load_reference(dbtrade_connection, dmp_engine, dmp_database, ref_row, swt_ref_id)

        logger.info("---- End of reference update ---->>>>")
        logger.info("RETURNCODE=0")
        logger.info("END script in %.2f sec", time.perf_counter() - start)
    except Exception:
        logger.exception("RETURNCODE=2")
        raise
    finally:
        close_connection(dbtrade_connection)
        close_connection(dmp_engine)


if __name__ == "__main__":
    main()
