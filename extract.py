import logging

import pandas as pd
from sqlalchemy import text

logger = logging.getLogger(__name__)


MASTER_PARAM_QUERY = """
SELECT
    a.pcm_ref_id,
    a.npnp_id,
    a.isis_techno,
    a.isis_tpr,
    b.ref_param_id,
    b.parameter_id,
    b.parameter_name,
    b.unit,
    b.pcm_group,
    b.merge_type,
    b.process_option,
    b.module,
    b.pcell,
    b.slm,
    b.npnp_id2,
    b.parameter_id2,
    b.parameter_name2,
    b.unit2,
    b.reptseq,
    b.report_variable
FROM t_pcm_ref_master a
LEFT JOIN t_pcm_ref_param b ON a.pcm_ref_id = b.pcm_ref_id
"""

REF_SPEC_QUERY = """
SELECT
    a.pcm_ref_id,
    a.npnp_id,
    a.isis_techno,
    a.isis_tpr,
    b.ref_param_id,
    b.parameter_id,
    c.ref_param_version_id,
    c.version,
    c.lsl,
    c.usl,
    c.low_control_limit,
    c.high_control_limit,
    c.low_cens_limit,
    c.high_cens_limit,
    c.lsl3,
    c.usl3,
    c.target,
    c.type,
    c.cr,
    c.cpk_flag
FROM (t_pcm_ref_master a
LEFT JOIN t_pcm_ref_param b ON a.pcm_ref_id = b.pcm_ref_id)
LEFT JOIN t_pcm_ref_spec c ON b.ref_param_id = c.ref_param_id
"""

REF_PARAM_LOOKUP_QUERY = """
SELECT
    a.isis_techno,
    a.isis_tpr,
    a.npnp_id,
    b.ref_param_id,
    b.parameter_id
FROM t_pcm_ref_master a
LEFT JOIN t_pcm_ref_param b ON a.pcm_ref_id = b.pcm_ref_id
"""

REF_SPEC_LOOKUP_QUERY = """
SELECT
    a.isis_techno,
    a.isis_tpr,
    a.npnp_id,
    b.ref_param_id,
    b.parameter_id,
    c.ref_param_version_id,
    c.version
FROM (t_pcm_ref_master a
LEFT JOIN t_pcm_ref_param b ON a.pcm_ref_id = b.pcm_ref_id)
LEFT JOIN t_pcm_ref_spec c ON b.ref_param_id = c.ref_param_id
"""


def read_datamart(engine, query, label):
    logger.info("Extract datamart: %s", label)
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn).drop_duplicates().reset_index(drop=True)


def read_source(engine, query, label):
    logger.info("Extract source: %s", label)
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn).drop_duplicates().reset_index(drop=True)


def sql_list(values):
    clean = pd.Series(values).dropna().astype(str).drop_duplicates()
    if clean.empty:
        return "''"
    return ", ".join("'" + value.replace("'", "''") + "'" for value in clean)


def extract_dbprod_npnpid(settings, dbprod_engine):
    query = f"""
        SELECT NLOCFAB, NPNPID, VERSION, CPROD, DDTEST
        FROM DBPROD.T_TLOTPNPI
        WHERE DDTEST >= '{settings["date_start"]}'
    """
    df = read_source(dbprod_engine, query, "recent npnp_id from T_TLOTPNPI")
    if df.empty:
        raise RuntimeError("ERROR FOUND ON DBPROD")

    return (
        df.assign(npnp_id=pd.to_numeric(df["NPNPID"], errors="coerce").astype("Int64"))
        [["npnp_id"]]
        .dropna()
        .drop_duplicates()
        .reset_index(drop=True)
    )


def extract_tpr(dbiltr_engine, npnp_ids):
    query = f"""
        SELECT
            NPNPID AS npnp_id,
            TECHNO AS isis_techno,
            TPR AS isis_tpr
        FROM DBILTR.T_TPR
        WHERE NPNPID IN ({sql_list(npnp_ids)})
    """
    df = read_source(dbiltr_engine, query, "TPR/TECHNO references")
    if df.empty:
        raise RuntimeError("ERROR FOUND ON DBILTR NPNPID TECHNO")
    df.columns = [column.lower() for column in df.columns]
    return df


def extract_dbiltr_param(dbiltr_engine, technos, tprs):
    query = f"""
        SELECT
            TECHNO AS isis_techno,
            TPR AS isis_tpr,
            NPARAM AS parameter_id,
            DESC_PARAM AS parameter_name,
            UNIT AS unit,
            GROUP AS pcm_group,
            MERGE_TYPE AS merge_type,
            REPORT AS process_option,
            MODULE_LIST AS module,
            PRIMITIVE_DEVICE AS pcell,
            SLM AS slm,
            STAT_HR AS npnp_id2,
            STAT_ALARM AS parameter_id2,
            F_DTS AS parameter_name2,
            AFFICHAGE AS unit2,
            F_PARAM AS reptseq,
            REPORT_VAR1 AS report_variable
        FROM DBILTR.T_PARAM
        WHERE TECHNO IN ({sql_list(technos)})
        AND TPR IN ({sql_list(tprs)})
    """
    df = read_source(dbiltr_engine, query, "parameter references")
    if df.empty:
        raise RuntimeError("ERROR FOUND ON DBILTR REF")
    df.columns = [column.lower() for column in df.columns]
    return df


def extract_dbiltr_spec(dbiltr_engine, technos, tprs):
    query = f"""
        SELECT
            lm.NPARAM AS parameter_id,
            lm.VERSION AS version,
            lm.LSP1 AS lsl,
            lm.HSP1 AS usl,
            lm.LSP2 AS low_control_limit,
            lm.HSP2 AS high_control_limit,
            lm.LCS AS low_cens_limit,
            lm.HCS AS high_cens_limit,
            lm.LSP3 AS lsl3,
            lm.HSP3 AS usl3,
            lm.TARGET AS target,
            lm.TYPE AS type,
            lm.CR_CODE AS cr,
            pa.F_CPK AS cpk_flag,
            lm.TPR AS isis_tpr,
            lm.TECHNO AS isis_techno
        FROM DBILTR.T_LIMITS lm
        INNER JOIN DBILTR.T_PARAM pa
            ON lm.TPR = pa.TPR
            AND lm.TECHNO = pa.TECHNO
            AND lm.NPARAM = pa.NPARAM
        WHERE lm.TECHNO IN ({sql_list(technos)})
        AND lm.TPR IN ({sql_list(tprs)})
    """
    df = read_source(dbiltr_engine, query, "parameter specs")
    if df.empty:
        raise RuntimeError("ERROR FOUND ON DBILTR REF SPEC")
    df.columns = [column.lower() for column in df.columns]
    return df


def extract_datamart_tables(engine):
    return {
        "ref_master": read_datamart(engine, "SELECT * FROM t_pcm_ref_master", "t_pcm_ref_master"),
        "ref_param": read_datamart(engine, MASTER_PARAM_QUERY, "t_pcm_ref_param"),
        "ref_spec": read_datamart(engine, REF_SPEC_QUERY, "t_pcm_ref_spec"),
        "ref_npnp": read_datamart(
            engine,
            "SELECT npnp_id, isis_techno, isis_tpr FROM t_pcm_ref_master",
            "master npnp lookup",
        ),
        "ref_param_lookup": read_datamart(engine, REF_PARAM_LOOKUP_QUERY, "parameter lookup"),
        "ref_spec_lookup": read_datamart(engine, REF_SPEC_LOOKUP_QUERY, "spec lookup"),
        "ref_vgroup": read_datamart(engine, "SELECT * FROM t_pcm_ref_vgroup", "t_pcm_ref_vgroup"),
    }
