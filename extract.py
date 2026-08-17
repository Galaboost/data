import logging

import pandas as pd
from sqlalchemy import bindparam, text


logger = logging.getLogger(__name__)


def _read_sql(engine, query, params=None, label="query", expanding_params=None):
    logger.info("Extract %s", label)
    statement = text(query)
    for param in expanding_params or ():
        statement = statement.bindparams(bindparam(param, expanding=True))

    with engine.connect() as connection:
        return pd.read_sql(statement, connection, params=params or {})


def extract_swt_profiles(dmp_engine):
    query = """
        SELECT profile_name,
               selected_npnpid,
               selected_version
        FROM t_profile_maps_master
    """
    return _read_sql(dmp_engine, query, label="SWT profiles from DMP")


def extract_nparams(dbprod_engine, npnpid, version):
    query = """
        SELECT nparam
        FROM DBPROD.T_TPARAMF
        WHERE npnpid = :npnpid
          AND version = :version
    """
    return _read_sql(
        dbprod_engine,
        query,
        params={"npnpid": str(npnpid), "version": str(version)},
        label=f"NPARAM list for npnpid={npnpid}, version={version}",
    )


def _extract_swt_measurements(
    dbprod_engine,
    *,
    data_table,
    value_column,
    npnpid,
    version,
    nparams,
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
          AND a.nparam IN :nparams
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
            "nparams": [str(value).strip() for value in nparams],
            "start_date": start_date,
            "end_date": end_date,
        },
        label=label,
        expanding_params=("nparams",),
    )


def extract_lot_measurements(dbprod_engine, npnpid, version, nparams, start_date, end_date):
    parametric = _extract_swt_measurements(
        dbprod_engine,
        data_table="T_TLOTPARF",
        value_column="qvl50pc",
        npnpid=npnpid,
        version=version,
        nparams=nparams,
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
        nparams=nparams,
        start_date=start_date,
        end_date=end_date,
        label=f"lot yield data npnpid={npnpid}",
        include_wafer=False,
    )
    return parametric, yield_data


def extract_wafer_measurements(dbprod_engine, npnpid, version, nparams, start_date, end_date):
    parametric = _extract_swt_measurements(
        dbprod_engine,
        data_table="T_TTRCPARF",
        value_column="qvl50pc",
        npnpid=npnpid,
        version=version,
        nparams=nparams,
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
        nparams=nparams,
        start_date=start_date,
        end_date=end_date,
        label=f"wafer yield data npnpid={npnpid}",
        include_wafer=True,
    )
    return parametric, yield_data
