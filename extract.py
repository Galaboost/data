import logging

import pandas as pd


logger = logging.getLogger(__name__)


def _read_sql(connection, query: str, label: str) -> pd.DataFrame:
    logger.info("Extract %s", label)
    if hasattr(connection, "connect"):
        with connection.connect() as conn:
            return pd.read_sql_query(query, conn).drop_duplicates().reset_index(drop=True)
    return pd.read_sql_query(query, connection).drop_duplicates().reset_index(drop=True)


def _sql_literals(values) -> str:
    clean = pd.Series(values).dropna().astype(str).str.strip().drop_duplicates()
    if clean.empty:
        return "''"
    return ", ".join("'" + value.replace("'", "''") + "'" for value in clean)


def extract_swt_profiles(dmp_engine) -> pd.DataFrame:
    query = """
        SELECT profile_name, selected_npnpid, selected_version
        FROM t_profile_maps_master
    """
    df = _read_sql(dmp_engine, query, "SWT profiles from DMP")
    if df.empty:
        return pd.DataFrame(columns=["techno", "npnpid", "version"])

    df.columns = [column.lower() for column in df.columns]
    result = pd.DataFrame(
        {
            "techno": df["profile_name"].astype(str).str.extract(r"([A-Za-z0-9]+)", expand=False),
            "npnpid": df["selected_npnpid"].astype(str).str.strip(),
            "version": df["selected_version"].astype(str).str.strip(),
        }
    )
    return result.dropna().drop_duplicates().sort_values(["techno", "npnpid", "version"]).reset_index(drop=True)


def extract_available_nparams(dbprod_engine, npnpid: str, version: str) -> list[int]:
    query = f"""
        SELECT nparam
        FROM DBPROD.T_TPARAMF
        WHERE npnpid = '{npnpid}'
        AND version = '{version}'
    """
    df = _read_sql(dbprod_engine, query, f"available NPARAM for {npnpid}/{version}")
    if df.empty:
        return []
    column = "nparam" if "nparam" in df.columns else "NPARAM"
    return pd.to_numeric(df[column], errors="coerce").dropna().astype(int).drop_duplicates().tolist()


def extract_lot_data(dbprod_engine, npnpid: str, version: str, nparams, start_date, end_date) -> pd.DataFrame:
    nparam_sql = _sql_literals(nparams)
    query_param = f"""
        SELECT a.nlocfab, a.ddtest, a.npnpid, a.version, a.nparam,
               a.qvl50pc AS value, substr(t.tparam, 1, 35) AS tparam
        FROM DBPROD.T_TLOTPARF AS a
        INNER JOIN DBPROD.T_TPARAMF AS t
            ON a.npnpid = t.npnpid
            AND a.version = t.version
            AND a.nparam = t.nparam
        WHERE a.npnpid = '{npnpid}'
        AND a.version = '{version}'
        AND a.nparam IN ({nparam_sql})
        AND a.NLOCFAB IN (
            SELECT NLOCFAB
            FROM DBPROD.T_TLOTPNPF
            WHERE npnpid = '{npnpid}'
            AND version = '{version}'
            AND ddtest >= '{start_date}'
            AND ddtest <= '{end_date}'
        )
    """
    query_yield = f"""
        SELECT a.nlocfab, a.ddtest, a.npnpid, a.version, a.nparam,
               a.qyield AS value, substr(t.tparam, 1, 35) AS tparam
        FROM DBPROD.T_TLOTYLDF AS a
        INNER JOIN DBPROD.T_TPARAMF AS t
            ON a.npnpid = t.npnpid
            AND a.version = t.version
            AND a.nparam = t.nparam
        WHERE a.npnpid = '{npnpid}'
        AND a.version = '{version}'
        AND a.nparam IN ({nparam_sql})
        AND a.NLOCFAB IN (
            SELECT NLOCFAB
            FROM DBPROD.T_TLOTPNPF
            WHERE npnpid = '{npnpid}'
            AND version = '{version}'
            AND ddtest >= '{start_date}'
            AND ddtest <= '{end_date}'
        )
    """
    return pd.concat(
        [
            _read_sql(dbprod_engine, query_param, f"lot param data {npnpid}/{version}"),
            _read_sql(dbprod_engine, query_yield, f"lot yield data {npnpid}/{version}"),
        ],
        ignore_index=True,
    )


def extract_wafer_data(dbprod_engine, npnpid: str, version: str, nparams, start_date, end_date) -> pd.DataFrame:
    nparam_sql = _sql_literals(nparams)
    query_param = f"""
        SELECT a.nlocfab, a.ntranch, a.ddtest, a.npnpid, a.version, a.nparam,
               a.qvl50pc AS value, substr(t.tparam, 1, 35) AS tparam
        FROM DBPROD.T_TTRCPARF AS a
        INNER JOIN DBPROD.T_TPARAMF AS t
            ON a.npnpid = t.npnpid
            AND a.version = t.version
            AND a.nparam = t.nparam
        WHERE a.npnpid = '{npnpid}'
        AND a.version = '{version}'
        AND a.nparam IN ({nparam_sql})
        AND a.NLOCFAB IN (
            SELECT NLOCFAB
            FROM DBPROD.T_TLOTPNPF
            WHERE npnpid = '{npnpid}'
            AND version = '{version}'
            AND ddtest >= '{start_date}'
            AND ddtest <= '{end_date}'
        )
    """
    query_yield = f"""
        SELECT a.nlocfab, a.ntranch, a.ddtest, a.npnpid, a.version, a.nparam,
               a.qyield AS value, substr(t.tparam, 1, 35) AS tparam
        FROM DBPROD.T_TTRCYLDF AS a
        INNER JOIN DBPROD.T_TPARAMF AS t
            ON a.npnpid = t.npnpid
            AND a.version = t.version
            AND a.nparam = t.nparam
        WHERE a.npnpid = '{npnpid}'
        AND a.version = '{version}'
        AND a.nparam IN ({nparam_sql})
        AND a.NLOCFAB IN (
            SELECT NLOCFAB
            FROM DBPROD.T_TLOTPNPF
            WHERE npnpid = '{npnpid}'
            AND version = '{version}'
            AND ddtest >= '{start_date}'
            AND ddtest <= '{end_date}'
        )
    """
    return pd.concat(
        [
            _read_sql(dbprod_engine, query_param, f"wafer param data {npnpid}/{version}"),
            _read_sql(dbprod_engine, query_yield, f"wafer yield data {npnpid}/{version}"),
        ],
        ignore_index=True,
    )
