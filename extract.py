import logging

import pandas as pd
from sqlalchemy import text


logger = logging.getLogger(__name__)


def _read_sql(engine, query, params=None, label="query"):
    logger.info("Extract %s", label)
    with engine.connect() as connection:
        return pd.read_sql(text(query), connection, params=params or {})


def extract_swt_profiles(dmp_engine):
    query = """
        SELECT profile_name,
               selected_npnpid,
               selected_version
        FROM t_profile_maps_master
    """
    return _read_sql(dmp_engine, query, label="SWT profiles from DMP")


def _extract_swt_measurements(
    dbprod_engine,
    *,
    data_table,
    value_column,
    npnpid,
    version,
    start_date,
    end_date,
    label,
    include_wafer,
):
    wafer_column = "a.ntranch," if include_wafer else ""
    query = f"""
        SELECT a.nlocfab,
               {wafer_column}
               a.ddtest,
               a.npnpid,
               a.version,
               a.nparam,
               a.{value_column} AS value,
               SUBSTR(t.tparam, 1, 35) AS tparam
        FROM DBPROD.{data_table} AS a
        INNER JOIN DBPROD.T_TPARAMF AS t
            ON a.npnpid = t.npnpid
           AND a.version = t.version
           AND a.nparam = t.nparam
        WHERE a.npnpid = :npnpid
          AND a.version = :version
          AND a.nlocfab IN (
              SELECT nlocfab
              FROM DBPROD.T_TLOTPNPF
              WHERE npnpid = :npnpid
                AND version = :version
                AND ddtest >= :start_date
                AND ddtest <= :end_date
          )
    """
    return _read_sql(
        dbprod_engine,
        query,
        params={
            "npnpid": str(npnpid),
            "version": str(version),
            "start_date": start_date,
            "end_date": end_date,
        },
        label=label,
    )


def extract_lot_measurements(dbprod_engine, npnpid, version, start_date, end_date):
    parametric = _extract_swt_measurements(
        dbprod_engine,
        data_table="T_TLOTPARF",
        value_column="qvl50pc",
        npnpid=npnpid,
        version=version,
        start_date=start_date,
        end_date=end_date,
        label=f"lot parametric data npnpid={npnpid}",
        include_wafer=False,
    )
    yield_data = _extract_swt_measurements(
        dbprod_engine,
        data_table="T_TLOTYLDF",
        value_column="qyield",
        npnpid=npnpid,
        version=version,
        start_date=start_date,
        end_date=end_date,
        label=f"lot yield data npnpid={npnpid}",
        include_wafer=False,
    )
    return parametric, yield_data


def extract_wafer_measurements(dbprod_engine, npnpid, version, start_date, end_date):
    parametric = _extract_swt_measurements(
        dbprod_engine,
        data_table="T_TTRCPARF",
        value_column="qvl50pc",
        npnpid=npnpid,
        version=version,
        start_date=start_date,
        end_date=end_date,
        label=f"wafer parametric data npnpid={npnpid}",
        include_wafer=True,
    )
    yield_data = _extract_swt_measurements(
        dbprod_engine,
        data_table="T_TTRCYLDF",
        value_column="qyield",
        npnpid=npnpid,
        version=version,
        start_date=start_date,
        end_date=end_date,
        label=f"wafer yield data npnpid={npnpid}",
        include_wafer=True,
    )
    return parametric, yield_data
