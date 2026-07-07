import logging

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


def load_emap(df_emap, dmp_engine):
    append_table(df_emap, dmp_engine, "t_emap")


def load_ret(df_ret, dmp_engine):
    append_table(df_ret, dmp_engine, "t_ret")


def load_die(df_die, dmp_engine):
    append_table(df_die, dmp_engine, "t_die")


def update_emap(df_emap, dmp_engine, emap_id):
    if df_emap.empty:
        logger.info("Skip t_emap update: no row")
        return

    row = df_emap.iloc[0].to_dict()
    row["emap_id"] = int(emap_id)
    query = text(
        """
        UPDATE dmp.t_emap
        SET sapn = :sapn,
            maskset_name = :maskset_name,
            version = :version,
            filename = :filename,
            effective_fra_datetime = :effective_fra_datetime,
            ret_x_size = :ret_x_size,
            ret_y_size = :ret_y_size,
            ret_y_vs_x_ratio = :ret_y_vs_x_ratio,
            ret_x_max = :ret_x_max,
            ret_y_max = :ret_y_max,
            die_qty = :die_qty,
            die_x_size = :die_x_size,
            die_y_size = :die_y_size,
            die_y_vs_x_ratio = :die_y_vs_x_ratio,
            die_x_max = :die_x_max,
            die_y_max = :die_y_max,
            swt_die_x_offset = :swt_die_x_offset,
            swt_die_y_offset = :swt_die_y_offset
        WHERE emap_id = :emap_id
        """
    )
    with dmp_engine.begin() as connection:
        connection.execute(query, row)
    logger.info("Updated t_emap emap_id=%s", emap_id)


def update_ret_test_types(df_ret_update, dmp_engine):
    if df_ret_update.empty:
        logger.info("Skip t_ret update: no matching ret row")
        return

    query = text(
        """
        UPDATE dmp.t_ret
        SET test_ret_type = :test_ret_type
        WHERE ret_id = :ret_id
          AND emap_id = :emap_id
          AND ret_x = :ret_x
          AND ret_y = :ret_y
        """
    )
    rows = df_ret_update[
        ["ret_id", "emap_id", "ret_x", "ret_y", "test_ret_type"]
    ].to_dict("records")
    with dmp_engine.begin() as connection:
        connection.execute(query, rows)
    logger.info("Updated %s t_ret test_ret_type row(s)", len(rows))
