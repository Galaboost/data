import logging

import pandas as pd


logger = logging.getLogger(__name__)


def append_table(dmp_engine, table_name: str, df: pd.DataFrame) -> int:
    if df.empty:
        logger.info("Skip %s: no row to load", table_name)
        return 0

    df.to_sql(table_name, dmp_engine, if_exists="append", index=False)
    logger.info("Loaded %s row(s) into %s", len(df), table_name)
    return len(df)


def load_ref_master(dmp_engine, df: pd.DataFrame) -> int:
    return append_table(dmp_engine, "t_swt_ref_master", df)


def load_ref_param(dmp_engine, df: pd.DataFrame) -> int:
    return append_table(dmp_engine, "t_swt_ref_param", df)


def load_ref_yield(dmp_engine, df: pd.DataFrame) -> int:
    return append_table(dmp_engine, "t_swt_ref_yield", df)


def load_ref_analog(dmp_engine, df: pd.DataFrame) -> int:
    return append_table(dmp_engine, "t_swt_ref_analog", df)
