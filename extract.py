import logging
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import text


logger = logging.getLogger(__name__)


def _read_sql(connection, query, label):
    logger.info("Extract %s", label)
    if hasattr(connection, "connect"):
        with connection.connect() as conn:
            return pd.read_sql(text(query), conn)
    return pd.read_sql_query(query, connection)


def _sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def extract_recent_index_refs(dbtrade_connection, lookback_days):
    start_date = date.today() - timedelta(days=lookback_days)
    query = f"""
        SELECT NPNPID, VERSION, PROD_CODE
        FROM ACLFT.T_INDEX
        WHERE DATE(DTCDRMAJ) >= {_sql_literal(start_date)}
        AND NB_TR_RECUES > 0
    """
    return _read_sql(dbtrade_connection, query, "recent DBTRADE T_INDEX references")


def extract_histo_master_refs(dbtrade_connection):
    query = """
        SELECT QUERY
        FROM ACLFTR.T_HISTO
        WHERE TABLE='ACLFTR.T_MASTER'
    """
    return _read_sql(dbtrade_connection, query, "ACLFTR.T_HISTO master references")


def extract_ref_master(dmp_engine):
    query = "SELECT * FROM t_swt_ref_master"
    return _read_sql(dmp_engine, query, "DMP t_swt_ref_master")


def extract_max_ref_param_id(dmp_engine, database):
    query = f"SELECT MAX(ref_param_id) AS max_id FROM {database}.t_swt_ref_param"
    df = _read_sql(dmp_engine, query, "max t_swt_ref_param.ref_param_id")
    if df.empty or pd.isna(df.loc[0, "max_id"]):
        return 0
    return int(df.loc[0, "max_id"])


def extract_ref_params(dmp_engine, database, swt_ref_id):
    query = f"""
        SELECT ref_param_id, swt_ref_id, parameter_id, yield_test
        FROM {database}.t_swt_ref_param
        WHERE swt_ref_id = {int(swt_ref_id)}
    """
    return _read_sql(dmp_engine, query, f"DMP reference parameters for swt_ref_id={swt_ref_id}")


def extract_yield_parameters(dbtrade_connection, npnp_id, version, product_code):
    query = f"""
        SELECT NPARAM AS parameter_id,
               DESC_PARAM AS parameter_name,
               NPNPID,
               VERSION
        FROM ACLFTR.T_YIELD
        WHERE NPNPID IN ({_sql_literal(npnp_id)})
        AND VERSION IN ({_sql_literal(version)})
        AND PROD_CODE IN ({_sql_literal(product_code)})
    """
    return _read_sql(dbtrade_connection, query, f"yield parameters {npnp_id}/{version}/{product_code}")


def extract_analog_parameters(dbtrade_connection, npnp_id, version, product_code):
    query = f"""
        SELECT NPARAM AS parameter_id,
               DESC_PARAM AS parameter_name,
               NPNPID,
               VERSION
        FROM ACLFTR.T_PARAM
        WHERE NPNPID IN ({_sql_literal(npnp_id)})
        AND VERSION IN ({_sql_literal(version)})
        AND PROD_CODE IN ({_sql_literal(product_code)})
    """
    return _read_sql(dbtrade_connection, query, f"analog parameters {npnp_id}/{version}/{product_code}")


def extract_yield_limits(dbtrade_connection, npnp_id, version, product_code):
    query = f"""
        SELECT NPARAM AS parameter_id,
               YIELD_TYPE,
               CAL_REGION,
               CONDITION
        FROM ACLFTR.T_YIELD
        WHERE NPNPID IN ({_sql_literal(npnp_id)})
        AND VERSION IN ({_sql_literal(version)})
        AND PROD_CODE IN ({_sql_literal(product_code)})
    """
    return _read_sql(dbtrade_connection, query, f"yield limits {npnp_id}/{version}/{product_code}")


def extract_analog_limits(dbtrade_connection, npnp_id, version, product_code):
    query = f"""
        SELECT NPARAM AS parameter_id,
               NUNIT AS unit,
               QTL AS lsl,
               QTH AS usl,
               QDL AS low_control_limit,
               QDH AS high_control_limit,
               QCL AS low_cens_limit,
               QCH AS high_cens_limit
        FROM ACLFTR.T_PARAM
        WHERE NPNPID IN ({_sql_literal(npnp_id)})
        AND VERSION IN ({_sql_literal(version)})
        AND PROD_CODE IN ({_sql_literal(product_code)})
    """
    return _read_sql(dbtrade_connection, query, f"analog limits {npnp_id}/{version}/{product_code}")


def extract_detected_reference_data(dbtrade_connection, dmp_engine, lookback_days):
    return {
        "index_refs": extract_recent_index_refs(dbtrade_connection, lookback_days),
        "histo_refs": extract_histo_master_refs(dbtrade_connection),
        "ref_master": extract_ref_master(dmp_engine),
    }


def extract_reference_parameters(dbtrade_connection, dmp_engine, database, reference):
    npnp_id = int(reference.npnp_id)
    version = int(reference.version)
    product_code = str(reference.product_code)
    swt_ref_id = int(reference.swt_ref_id)

    return {
        "last_param_id": extract_max_ref_param_id(dmp_engine, database),
        "yield_params": extract_yield_parameters(
            dbtrade_connection,
            npnp_id,
            version,
            product_code,
        ),
        "analog_params": extract_analog_parameters(
            dbtrade_connection,
            npnp_id,
            version,
            product_code,
        ),
        "yield_limits": extract_yield_limits(
            dbtrade_connection,
            npnp_id,
            version,
            product_code,
        ),
        "analog_limits": extract_analog_limits(
            dbtrade_connection,
            npnp_id,
            version,
            product_code,
        ),
        "ref_params": extract_ref_params(dmp_engine, database, swt_ref_id),
    }
