import logging
import sys

import pandas as pd
from sqlalchemy import text

from config_reftool import connect_to_dmp, connect_to_reftool


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


REFTOOL_QUERY = """
    SELECT OPERATION AS operation,
           ATELIER AS toolshop,
           CATEGORIE AS category,
           TYPE_PC AS proccard_type,
           TYPE_GATE AS gate_type
    FROM reftool.T_MASTER_OPERATION_LIST
"""

DMP_QUERY = "SELECT * FROM t_oper_admin"

UPDATE_T_OPER_ADMIN = text(
    """
    UPDATE `dmp`.`t_oper_admin`
    SET `toolshop` = :toolshop,
        `category` = :category,
        `proccard_type` = :proccard_type,
        `gate_type` = :gate_type,
        `admin_check` = :admin_check
    WHERE `operation` = :operation
    """
)


def read_sql(engine, query):
    with engine.connect() as connection:
        return pd.read_sql(text(query), connection)


def anti_join(left, right, by):
    """Pandas equivalent of dplyr::anti_join(left, right, by=by)."""
    right_keys = right[by].drop_duplicates()
    merged = left.merge(right_keys, on=by, how="left", indicator=True)
    return merged.loc[merged["_merge"] == "left_only", left.columns].copy()


def extract_reftool():
    logger.info("extraction from reftool begin")

    reftool_engine = connect_to_reftool()
    dbget = read_sql(reftool_engine, REFTOOL_QUERY)

    dbget["admin_check"] = dbget["category"].isin(["VAO", "TEST_ELEC"]).astype(int)
    dbget = dbget.sort_values("operation").reset_index(drop=True)

    dcheck = dbget[["operation"]].drop_duplicates()
    logger.info(
        "Extraction from reftool end,number of references: %s",
        len(dcheck),
    )
    return dbget, dcheck


def extract_dmp():
    logger.info("Extraction from dmp begin")

    dmp_engine = connect_to_dmp()
    df_from_datamart = read_sql(dmp_engine, DMP_QUERY)

    logger.info(
        "Extraction from dmp end,number of references: %s",
        len(df_from_datamart),
    )
    return df_from_datamart


def transform(dbget, df_from_datamart):
    compare_columns = [
        "operation",
        "toolshop",
        "category",
        "proccard_type",
        "gate_type",
        "admin_check",
    ]

    db_create = anti_join(dbget, df_from_datamart, by=["operation"])
    db_update = anti_join(dbget, df_from_datamart, by=compare_columns)
    db_update = anti_join(db_update, db_create, by=compare_columns)

    logger.info("Number of line created: %s", len(db_create))
    logger.info("Number of line updated: %s", len(db_update))

    return db_create, db_update


def load_creates(dmp_engine, db_create):
    if db_create.empty:
        return

    with dmp_engine.begin() as connection:
        db_create.to_sql(
            "t_oper_admin",
            connection,
            if_exists="append",
            index=False,
            method="multi",
        )


def load_updates(dmp_engine, db_update):
    if db_update.empty:
        return

    update_rows = db_update[
        [
            "operation",
            "toolshop",
            "category",
            "proccard_type",
            "gate_type",
            "admin_check",
        ]
    ].to_dict(orient="records")

    with dmp_engine.begin() as connection:
        for row in update_rows:
            connection.execute(UPDATE_T_OPER_ADMIN, row)


def main():
    res = True

    try:
        dbget, dcheck = extract_reftool()
        df_from_datamart = extract_dmp()

        if res is True:
            try:
                res = len(dcheck) > 0
            except Exception as exc:
                res = f"ERROR FOUND ON REFTOOL QUERY {exc}"

        if res is True:
            try:
                res = len(df_from_datamart) > 0
            except Exception as exc:
                res = f"ERROR FOUND ON dmp {exc}"

        db_create, db_update = transform(dbget, df_from_datamart)

        dmp_engine = connect_to_dmp()
        load_creates(dmp_engine, db_create)
        load_updates(dmp_engine, db_update)

    except Exception as exc:
        logger.exception("Fatal error, stop ETL...")
        res = str(exc)

    if res is True:
        logger.info("RETURNCODE=0")
        return_code = 0
    else:
        logger.info(res)
        logger.info("RETURNCODE=2")
        return_code = 2

    return return_code


if __name__ == "__main__":
    sys.exit(main())
