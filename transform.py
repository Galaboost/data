import pandas as pd


def normalize_dbprod_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [column.upper() for column in result.columns]
    return result


def normalize_ddtest(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
    fallback = series.astype(str).str.strip()
    return parsed.dt.strftime("%Y-%m-%d").fillna(fallback)


def _format_tparam(row, pmax: int) -> str:
    nparam = pd.to_numeric(row["NPARAM"], errors="coerce")
    tparam = str(row["TPARAM"]).replace(" ", "").strip()
    if pd.notna(nparam) and nparam < pmax:
        return f"t{int(nparam)}_{tparam}"
    return tparam


def reshape_swt_data(df: pd.DataFrame, pmax: int, id_columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    result = normalize_dbprod_columns(df)
    for column in ["NLOCFAB", "NTRANCH", "NPNPID", "VERSION", "TPARAM"]:
        if column in result.columns:
            result[column] = result[column].astype(str).str.strip()

    result["TPARAM"] = result.apply(_format_tparam, axis=1, pmax=pmax)
    result["DDTEST"] = normalize_ddtest(result["DDTEST"])

    pivoted = result.pivot_table(
        index=id_columns,
        columns="TPARAM",
        values="VALUE",
        aggfunc="last",
    ).reset_index()
    pivoted.columns.name = None
    return pivoted.sort_values(id_columns).reset_index(drop=True)


def merge_with_archive(
    archive_df: pd.DataFrame | None,
    new_df: pd.DataFrame,
    group_columns: list[str],
    sort_columns: list[str],
) -> tuple[pd.DataFrame, int]:
    if new_df.empty:
        return archive_df.copy() if archive_df is not None else pd.DataFrame(), 0

    if archive_df is None or archive_df.empty:
        result = new_df.drop_duplicates().sort_values(sort_columns).reset_index(drop=True)
        return result, result[group_columns].drop_duplicates().shape[0]

    archive = normalize_dbprod_columns(archive_df)
    archive["DDTEST"] = normalize_ddtest(archive["DDTEST"])
    new_lots = set(new_df["NLOCFAB"].dropna().astype(str)) - set(archive["NLOCFAB"].dropna().astype(str))

    result = pd.concat([archive, new_df], ignore_index=True, sort=False).drop_duplicates()
    result["DDTEST_SORT"] = pd.to_datetime(result["DDTEST"], errors="coerce")
    result = (
        result.sort_values(sort_columns + ["DDTEST_SORT"])
        .groupby(group_columns, dropna=False, as_index=False)
        .tail(1)
        .drop(columns=["DDTEST_SORT"])
        .sort_values(sort_columns)
        .reset_index(drop=True)
    )
    return result, len(new_lots)


def transform_lot_data(raw_df: pd.DataFrame, pmax: int) -> pd.DataFrame:
    return reshape_swt_data(raw_df, pmax, ["NLOCFAB", "DDTEST", "NPNPID", "VERSION"])


def transform_wafer_data(raw_df: pd.DataFrame, pmax: int) -> pd.DataFrame:
    return reshape_swt_data(raw_df, pmax, ["NLOCFAB", "NTRANCH", "DDTEST", "NPNPID", "VERSION"])


def select_allgood_wafer(wafer_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["NPNPID", "DDTEST", "NLOCFAB", "NTRANCH", "AllGood"]
    missing = [column for column in columns if column not in wafer_df.columns]
    if missing:
        return pd.DataFrame(columns=columns)
    return wafer_df[columns].copy()
