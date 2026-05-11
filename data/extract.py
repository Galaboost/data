import pandas as pd
import logging


logger = logging.getLogger(__name__)


SYMARO_QUERIES = {
    "oper": """
        SELECT OPE_ID, OPE_NAME, OPE_COMMENT, OPE_UPD_TIME
        FROM T_OPERATION
    """,
    "rattachement": """
        SELECT RAT_ID, RAT_OPE_ID, RAT_PRODUCT_CODE, RAT_CODETECHNO, RAT_ROUTE_ID, RAT_UPD_TIME
        FROM T_RATTACHEMENT
    """,
    "destination": """
        SELECT DEST_ROUTE_ID, DEST_RAT_ID, DEST_ROUTE_DESCRIPTION
        FROM T_DESTINATION
    """,
    "route": """
        SELECT RTE_ID, RTE_NAME, RTE_UPD_TIME
        FROM T_ROUTE
    """,
}


DATAMART_QUERIES = {
    "device_cp": """
        SELECT DISTINCT substr(l.mes_lot_id, 1, 2) as product_code, d.device_id
        FROM t_lot l
        JOIN t_device d ON l.device_id = d.device_id
    """,
    "from_datamart_cp": """
        SELECT *
        FROM t_mes_ref_cp
    """,
    "from_datamart_route": """
        SELECT *
        FROM t_mes_ref_route
    """,
    "from_datamart_oper": """
        SELECT operation, route
        FROM t_mes_ref_oper
    """,
    "device": """
        SELECT device_id, local_process_family
        FROM t_device
    """,
}


def read_query(engine, query, label):
    logger.info("Loading %s", label)
    df = pd.read_sql(query, engine)
    df = df.drop_duplicates()
    logger.info("RETURNCODE=0")
    logger.info("Data acquisition %s OK", label)
    return df


def extract_symaro_data(engine):
    data = {}
    for label, query in SYMARO_QUERIES.items():
        data[label] = read_query(engine, query, label)
    return data


def extract_datamart_data(engine):
    data = {}
    for label, query in DATAMART_QUERIES.items():
        data[label] = read_query(engine, query, label)
    data["from_datamart_oper"] = data["from_datamart_oper"].drop_duplicates()
    return data


def extract_all(symaro_engine, datamart_engine):
    data = {}
    data.update(extract_symaro_data(symaro_engine))
    data.update(extract_datamart_data(datamart_engine))
    return data
