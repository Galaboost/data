import logging

import pandas as pd
from sqlalchemy import text

from config import DBMAPS_MAP_TYPE, SEND_TO_DB_UPDATE


logger = logging.getLogger(__name__)


def _read_sql(engine, query, params=None, label="query"):
    logger.info("Extract %s", label)
    with engine.connect() as connection:
        return pd.read_sql(text(query), connection, params=params or {})


def extract_devices_without_emap(dmp_engine):
    query = """
        SELECT A.*, B.emap_id
        FROM t_device A
        LEFT JOIN t_emap B ON A.device_id = B.device_id
        WHERE emap_id IS NULL
          AND A.maskset_name != 'KIT'
          AND A.maskset_name != 'PREPRO'
          AND A.maskset_name != ''
    """
    return _read_sql(dmp_engine, query, label="devices without emap")


def extract_devices_for_update(dmp_engine, emap_id=2299):
    query = """
        SELECT A.*, B.emap_id
        FROM t_device A
        LEFT JOIN t_emap B ON A.device_id = B.device_id
        WHERE B.emap_id = :emap_id
    """
    return _read_sql(
        dmp_engine,
        query,
        params={"emap_id": int(emap_id)},
        label=f"devices for emap update {emap_id}",
    )


def extract_devices(dmp_engine, send_to_db):
    if send_to_db == SEND_TO_DB_UPDATE:
        return extract_devices_for_update(dmp_engine)
    return extract_devices_without_emap(dmp_engine)


def latest_map0_header_query(select_clause):
    return f"""
        SELECT DISTINCT {select_clause}
        FROM dbmaps.map0_header t1
        LEFT JOIN dbmaps.map0_header t2
          ON t1.DESIGN = t2.DESIGN
         AND t1.MAP_TYPE = t2.MAP_TYPE
         AND t1.DT_EFFET < t2.DT_EFFET
        WHERE (
                (t2.DT_EFFET IS NULL AND t2.VERSION IS NULL AND t1.COMMENT NOT LIKE '%FROM STIF%')
                OR (t2.COMMENT LIKE '%FROM STIF%' AND t1.COMMENT NOT LIKE '%FROM STIF%')
            )
          AND t1.CHIP_COUNT != 1
          AND t1.MAP_TYPE = :map_type
          AND t1.DT_EFFET IS NOT NULL
          AND t1.DESIGN = :design
    """


def extract_map0_rows(dbmaps_engine, maskset_name):
    query = latest_map0_header_query("t1.*")
    return _read_sql(
        dbmaps_engine,
        query,
        params={"map_type": DBMAPS_MAP_TYPE, "design": maskset_name},
        label=f"dbmaps.map0_header file {maskset_name}/{DBMAPS_MAP_TYPE}",
    )


def extract_map0_info(dbmaps_engine, maskset_name):
    select_clause = """
        t1.SAPN,
        t1.DESIGN,
        t1.VERSION,
        t1.MAP_TYPE,
        t1.CHIP_COUNT,
        t1.COLCNT,
        t1.ROWCNT,
        t1.XDIES,
        t1.YDIES,
        t1.COMMENT,
        t1.MAJ_DATE,
        t1.DT_EFFET
    """
    query = latest_map0_header_query(select_clause)
    return _read_sql(
        dbmaps_engine,
        query,
        params={"map_type": DBMAPS_MAP_TYPE, "design": maskset_name},
        label=f"dbmaps.map0_header info {maskset_name}/{DBMAPS_MAP_TYPE}",
    )


def extract_t_emap(dmp_engine):
    return _read_sql(dmp_engine, "SELECT * FROM t_emap", label="t_emap")


def extract_t_ret(dmp_engine):
    return _read_sql(dmp_engine, "SELECT * FROM t_ret", label="t_ret")


def extract_existing_rets_for_maskset(dmp_engine, maskset_name):
    query = """
        SELECT a.ret_id,
               a.emap_id,
               a.ret_x,
               a.ret_y,
               a.ret_type,
               a.center_mm_distance
        FROM t_ret a
        JOIN t_emap b ON a.emap_id = b.emap_id
        WHERE b.maskset_name = :maskset_name
    """
    return _read_sql(
        dmp_engine,
        query,
        params={"maskset_name": maskset_name},
        label=f"existing rets for {maskset_name}",
    )
