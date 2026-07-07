import logging
import time
from pathlib import Path

from config import (
    SEND_TO_DB_INSERT,
    SEND_TO_DB_UPDATE,
    connect_to_dbmaps,
    connect_to_dmp,
    get_device_limit,
    get_send_to_db,
)
from extract import (
    extract_devices,
    extract_existing_rets_for_maskset,
    extract_map0_info,
    extract_map0_rows,
    extract_t_emap,
    extract_t_ret,
)
from load import load_die, load_emap, load_ret, update_emap, update_ret_test_types
from transform import (
    build_device_payload,
    build_ret_update_rows,
    build_t_die,
    build_t_ret,
    normalize_device_row,
    prepare_devices,
    should_skip_device,
)


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "DBMAPS_TO_DATAMART.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def process_device(device_row, dmp_engine, dbmaps_engine, send_to_db):
    if should_skip_device(device_row):
        logger.info("Skip device with empty maskset_name")
        return None

    device_row = normalize_device_row(device_row)
    maskset_name = str(device_row["maskset_name"])
    logger.info("Map Creation for %s", maskset_name)

    maps_rows = extract_map0_rows(dbmaps_engine, maskset_name)
    map0_info = extract_map0_info(dbmaps_engine, maskset_name)
    payload = build_device_payload(device_row, maps_rows, map0_info)

    if payload["emap"].empty:
        raise ValueError(f"ERROR FOUND ON DBMAPS: no emap created for {maskset_name}")

    if send_to_db == SEND_TO_DB_INSERT:
        load_emap(payload["emap"], dmp_engine)
    elif send_to_db == SEND_TO_DB_UPDATE:
        update_emap(payload["emap"], dmp_engine, device_row["emap_id"])
    else:
        logger.info("DB load disabled by DBMAPS_SEND_TO_DB=%s", send_to_db)

    t_emap = extract_t_emap(dmp_engine)
    t_ret_payload = build_t_ret(payload["ret_emap"], t_emap)

    if send_to_db == SEND_TO_DB_UPDATE:
        existing_rets = extract_existing_rets_for_maskset(dmp_engine, maskset_name)
        ret_update_rows = build_ret_update_rows(existing_rets, t_ret_payload)
        update_ret_test_types(ret_update_rows, dmp_engine)
    elif send_to_db == SEND_TO_DB_INSERT:
        load_ret(t_ret_payload, dmp_engine)

    t_ret = extract_t_ret(dmp_engine)
    t_die_payload = build_t_die(payload["die_ret_emap"], t_emap, t_ret)

    if t_die_payload.empty:
        raise ValueError(
            f"ERROR FOUND ON ETL dbmaps_to_datamart: die creation fail for {maskset_name}"
        )

    if send_to_db == SEND_TO_DB_INSERT:
        load_die(t_die_payload, dmp_engine)

    return {
        "maskset_name": maskset_name,
        "emap_rows": len(payload["emap"]),
        "ret_rows": len(t_ret_payload),
        "die_rows": len(t_die_payload),
    }


def run_etl():
    start_time = time.perf_counter()
    send_to_db = get_send_to_db()
    device_limit = get_device_limit()
    results = []

    dmp_engine = connect_to_dmp()
    dbmaps_engine = connect_to_dbmaps()
    try:
        devices = prepare_devices(extract_devices(dmp_engine, send_to_db), device_limit)
        logger.info("%s device(s) selected", len(devices))

        for _, device_row in devices.iterrows():
            result = process_device(device_row, dmp_engine, dbmaps_engine, send_to_db)
            if result:
                results.append(result)

        logger.info("End ETL in %.2f sec", time.perf_counter() - start_time)
        return results
    finally:
        dmp_engine.dispose()
        dbmaps_engine.dispose()


if __name__ == "__main__":
    run_etl()
