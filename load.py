import logging

import pandas as pd
from sqlalchemy import text


logger = logging.getLogger(__name__)


def append_table(df, dmp_engine, table_name):
    if df.empty:
        logger.info("Skip %s: no row to load", table_name)
        return

    with dmp_engine.begin() as connection:
        df.to_sql(
            table_name,
            connection,
            if_exists="append",
            index=False,
            method="multi",
        )
    logger.info("Loaded %s row(s) into %s", len(df), table_name)


def load_ref_master(df_ref_master, dmp_engine):
    # SQL equivalent:
    # INSERT INTO t_swt_ref_master
    #     (swt_ref_id, npnp_id, version, product_code,
    #      swt_ref_fra_datetime, load_file_name, comment)
    # VALUES
    #     (:swt_ref_id, :npnp_id, :version, :product_code,
    #      :swt_ref_fra_datetime, :load_file_name, :comment)
    append_table(df_ref_master, dmp_engine, "t_swt_ref_master")


def load_ref_param(df_ref_param, dmp_engine):
    # SQL equivalent:
    # INSERT INTO t_swt_ref_param
    #     (ref_param_id, swt_ref_id, parameter_id, parameter_name, yield_test)
    # VALUES
    #     (:ref_param_id, :swt_ref_id, :parameter_id, :parameter_name, :yield_test)
    append_table(df_ref_param, dmp_engine, "t_swt_ref_param")


def load_ref_yield(df_ref_yield, dmp_engine):
    # SQL equivalent:
    # INSERT INTO t_swt_ref_yield
    #     (ref_param_id, yield_type, cal_region, condition)
    # VALUES
    #     (:ref_param_id, :yield_type, :cal_region, :condition)
    append_table(df_ref_yield, dmp_engine, "t_swt_ref_yield")


def load_ref_analog(df_ref_analog, dmp_engine):
    # SQL equivalent:
    # INSERT INTO t_swt_ref_analog
    #     (ref_param_id, unit, lsl, usl,
    #      low_control_limit, high_control_limit,
    #      low_cens_limit, high_cens_limit)
    # VALUES
    #     (:ref_param_id, :unit, :lsl, :usl,
    #      :low_control_limit, :high_control_limit,
    #      :low_cens_limit, :high_cens_limit)
    append_table(df_ref_analog, dmp_engine, "t_swt_ref_analog")


def load_reference_payload(payload, dmp_engine):
    load_ref_master(payload["ref_master"], dmp_engine)
    load_ref_param(payload["ref_param"], dmp_engine)
    load_ref_yield(payload["ref_yield"], dmp_engine)
    load_ref_analog(payload["ref_analog"], dmp_engine)
