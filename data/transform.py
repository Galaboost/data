import logging

import pandas as pd


logger = logging.getLogger(__name__)


def latest_by_timestamp(df, group_column, timestamp_column):
    result = df.copy()
    result[timestamp_column] = pd.to_datetime(result[timestamp_column])
    latest = (
        result.groupby(group_column, as_index=False)[timestamp_column]
        .max()
        .rename(columns={timestamp_column: "last_value"})
    )
    result = result.merge(
        latest,
        left_on=[group_column, timestamp_column],
        right_on=[group_column, "last_value"],
    )
    return result.drop(columns=["last_value"]).drop_duplicates()


def build_alternative_routes(data):
    df_oper = data["oper"].drop_duplicates().copy()
    df_rattachement = data["rattachement"].drop_duplicates().copy()
    df_destination = data["destination"].drop_duplicates().copy()
    df_route = data["route"].drop_duplicates().copy()
    df_from_datamart = data["from_datamart_oper"].drop_duplicates().copy()

    df_oper["OPE_UPD_TIME"] = pd.to_datetime(df_oper["OPE_UPD_TIME"])
    df_route["RTE_UPD_TIME"] = pd.to_datetime(df_route["RTE_UPD_TIME"])
    df_route_latest = latest_by_timestamp(df_route, "RTE_NAME", "RTE_UPD_TIME")

    df_or = df_oper.merge(df_rattachement, left_on="OPE_ID", right_on="RAT_OPE_ID")
    df_ord = df_or.merge(df_destination, left_on="RAT_ID", right_on="DEST_RAT_ID")
    df_ordr = df_ord.merge(df_route_latest, left_on="DEST_ROUTE_ID", right_on="RTE_ID")
    df_ordrr = df_ordr.merge(
        df_route_latest,
        left_on="RAT_ROUTE_ID",
        right_on="RTE_ID",
        how="left",
        suffixes=(".x", ".y"),
    )
    df_ordro = df_from_datamart.merge(
        df_ordrr,
        left_on="operation",
        right_on="OPE_NAME",
    )

    df_ordro = df_ordro[
        (df_ordro["RTE_NAME.y"] == df_ordro["route"])
        | (df_ordro["RTE_NAME.y"].isna())
    ][["operation", "route", "RTE_NAME.x"]].drop_duplicates()

    df_ordro = df_ordro.reset_index(drop=True)
    df_ordro["alt"] = (
        df_ordro.groupby(["operation", "route"]).cumcount() + 1
    ).map(lambda value: f"alt_{value}")

    df_ordro_l = (
        df_ordro.pivot_table(
            index=["operation", "route"],
            columns="alt",
            values="RTE_NAME.x",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    return df_ordro, df_ordro_l


def split_process_family(df):
    result = df.copy()
    split_values = result["local_process_family"].astype("string").str.split(
        r"[^A-Za-z0-9.]+",
        n=1,
        expand=True,
        regex=True,
    )

    result["process_family"] = split_values[0]
    result["Route"] = split_values[1] if split_values.shape[1] > 1 else pd.NA
    return result


def build_device_routes(df_device):
    df_device = split_process_family(df_device)
    route_text = df_device["Route"].astype("string")

    df_device["route_1"] = route_text.str.slice(0, 2) + "00"
    df_device["route_2"] = route_text.str.slice(2, 4) + "00"
    df_device["route_3"] = route_text.str.slice(4, 6) + "00"

    df_device_l = df_device.melt(
        id_vars=["device_id", "local_process_family", "process_family", "Route"],
        value_vars=["route_1", "route_2", "route_3"],
        var_name="temp",
        value_name="Routes",
    )

    return df_device_l.dropna(subset=["Routes"])


def build_final_routes(data, df_ordro_l):
    df_device_l = build_device_routes(data["device"])
    df_from_datamart = data["from_datamart_oper"].drop_duplicates()

    df_route_oper = df_device_l.merge(
        df_from_datamart,
        left_on="Routes",
        right_on="route",
        how="left",
    )
    df_route_oper_alt = df_route_oper.merge(
        df_ordro_l,
        left_on=["Routes", "operation"],
        right_on=["route", "operation"],
        how="left",
        suffixes=("", "_altref"),
    )

    alt_columns = [column for column in df_route_oper_alt.columns if column.startswith("alt_")]

    if alt_columns:
        df_route_oper_alt_l = df_route_oper_alt.melt(
            id_vars=[column for column in df_route_oper_alt.columns if column not in alt_columns],
            value_vars=alt_columns,
            var_name="tempo",
            value_name="alt",
        ).dropna(subset=["alt"])
    else:
        df_route_oper_alt_l = df_route_oper_alt.copy()
        df_route_oper_alt_l["alt"] = pd.NA

    df_principal = (
        df_route_oper_alt_l[["process_family", "Routes", "device_id"]]
        .drop_duplicates()
        .assign(type="Main")
        .rename(columns={"Routes": "route"})
    )

    df_alternative = (
        df_route_oper_alt_l[["process_family", "alt", "device_id"]]
        .dropna(subset=["alt"])
        .drop_duplicates()
        .assign(type="Alternative")
        .rename(columns={"alt": "route"})
    )

    df_final = pd.concat([df_principal, df_alternative], ignore_index=True)
    df_final["process_family"] = df_final["process_family"].fillna("MISC")

    return df_final[["process_family", "route", "device_id", "type"]]


def anti_join(left, right, columns):
    existing = right[columns].drop_duplicates()
    merged = left.merge(existing, on=columns, how="left", indicator=True)
    return merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])


def transform_all(data):
    logger.info("Starting transformations")
    df_ordro, df_ordro_l = build_alternative_routes(data)
    df_final = build_final_routes(data, df_ordro_l)

    df_new_cp = anti_join(
        data["device_cp"],
        data["from_datamart_cp"],
        ["product_code", "device_id"],
    )
    df_new_route = anti_join(
        df_final,
        data["from_datamart_route"],
        ["process_family", "device_id", "route", "type"],
    )

    logger.info("RETURNCODE=0")
    logger.info("Transformations OK")

    return {
        "alternative_routes": df_ordro,
        "alternative_routes_wide": df_ordro_l,
        "final_routes": df_final,
        "new_cp": df_new_cp,
        "new_route": df_new_route,
    }
