import logging


logger = logging.getLogger(__name__)


def append_table(engine, table_name, df):
    if df.empty:
        logger.info("No rows to insert into %s", table_name)
        return 0

    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False,
        method="multi",
    )

    logger.info("Inserted %s rows into %s", len(df), table_name)
    return len(df)


def load_datamart(datamart_engine, results):
    route_count = append_table(datamart_engine, "t_mes_ref_route", results["new_route"])
    cp_count = append_table(datamart_engine, "t_mes_ref_cp", results["new_cp"])
    logger.info("RETURNCODE=0")
    logger.info("Load datamart OK")

    return {
        "route_rows": route_count,
        "cp_rows": cp_count,
    }
