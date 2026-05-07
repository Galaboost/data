from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from config import get_dmp_engine, get_symaro_engine


def read_sql_df(engine: Engine, query: str) -> pd.DataFrame:
    with engine.connect() as connection:
        return pd.read_sql(text(query), connection)


def latest_rows(df: pd.DataFrame, key_columns: list[str], time_column: str) -> pd.DataFrame:
    df = df.drop_duplicates().copy()
    df[time_column] = pd.to_datetime(df[time_column], errors="coerce")
    latest_time = df.groupby(key_columns, dropna=False)[time_column].transform("max")
    return df.loc[df[time_column].eq(latest_time)].drop_duplicates().copy()


def latest_proccard_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = latest_rows(df, ["PCA_NAME"], "PCA_UPD_TIME")
    latest_id = df.groupby("PCA_NAME", dropna=False)["PCA_ID"].transform("max")
    return df.loc[df["PCA_ID"].eq(latest_id)].drop_duplicates().copy()


def extract_symaro_data(symaro_engine: Engine | None = None) -> dict[str, pd.DataFrame]:
    engine = symaro_engine or get_symaro_engine()

    proccard = latest_proccard_rows(
        read_sql_df(
            engine,
            """
            SELECT PCA_ID, PCA_NAME, PCA_COMMENT, PCA_GATE_ID, PCA_GATE_COMMENT, PCA_UPD_TIME
            FROM T_PCARD
            """,
        )
    )

    proccardoper = latest_rows(
        read_sql_df(
            engine,
            """
            SELECT PCO_PCARD_ID, PCO_OPERATION_ID, PCO_SEQUENCE, PCO_UPD_TIME
            FROM TL_PCARD_OPER
            """,
        ),
        ["PCO_PCARD_ID", "PCO_OPERATION_ID"],
        "PCO_UPD_TIME",
    )

    oper = latest_rows(
        read_sql_df(
            engine,
            """
            SELECT OPE_ID, OPE_NAME, OPE_COMMENT, OPE_UPD_TIME
            FROM T_OPERATION
            """,
        ),
        ["OPE_NAME"],
        "OPE_UPD_TIME",
    )

    routepcard = read_sql_df(
        engine,
        """
        SELECT RTE_PCARD_ID, RTE_ROUTE_ID
        FROM TL_ROUTE_PCARDS
        """,
    ).drop_duplicates()

    route = latest_rows(
        read_sql_df(
            engine,
            """
            SELECT RTE_ID, RTE_NAME, RTE_UPD_TIME
            FROM T_ROUTE
            """,
        ),
        ["RTE_NAME"],
        "RTE_UPD_TIME",
    )

    gate = latest_rows(
        read_sql_df(
            engine,
            """
            SELECT GATE_ID, GATE_NAME, GATE_UPD_TIME
            FROM T_GATE
            """,
        ),
        ["GATE_NAME"],
        "GATE_UPD_TIME",
    )

    return {
        "proccard": proccard,
        "proccardoper": proccardoper,
        "oper": oper,
        "routepcard": routepcard,
        "route": route,
        "gate": gate,
    }


def extract_datamart_reference(dmp_engine: Engine | None = None) -> pd.DataFrame:
    engine = dmp_engine or get_dmp_engine()
    df = read_sql_df(engine, "SELECT * FROM t_mes_ref_oper")
    return df.drop(columns=["mes_ref_oper_id"], errors="ignore").drop_duplicates().copy()

