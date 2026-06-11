from datetime import datetime

import pandas as pd


REF_KEY_COLUMNS = ["npnp_id", "version", "product_code"]


def _lower_columns(df):
    result = df.copy()
    result.columns = [column.lower() for column in result.columns]
    return result


def _compact_product_code(series):
    return series.astype(str).str.replace(" ", "", regex=False).str.strip()


def _to_int(series):
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _one_year_ago(value):
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def transform_index_refs(df_index):
    if df_index.empty:
        return pd.DataFrame(columns=REF_KEY_COLUMNS + ["cprod"])

    df = _lower_columns(df_index).rename(
        columns={"npnpid": "npnp_id", "prod_code": "product_code"}
    )
    df = df[["npnp_id", "version", "product_code"]].drop_duplicates()
    df["npnp_id"] = _to_int(df["npnp_id"])
    df["version"] = _to_int(df["version"])
    df["product_code"] = _compact_product_code(df["product_code"])
    df["cprod"] = df["product_code"]
    return df.dropna(subset=["npnp_id", "version"]).drop_duplicates().sort_values(REF_KEY_COLUMNS).reset_index(drop=True)


def transform_histo_refs(df_histo):
    if df_histo.empty:
        return pd.DataFrame(columns=REF_KEY_COLUMNS + ["cprod"])

    df = _lower_columns(df_histo)
    rows = []
    for raw_query in df["query"].dropna().astype(str):
        parts = raw_query.split(",", 2)
        if len(parts) < 3:
            continue
        rows.append(
            {
                "npnp_id": parts[0].strip()[-4:],
                "version": parts[1].strip(),
                "product_code": parts[2].replace(",", "").strip(),
            }
        )

    result = pd.DataFrame(rows, columns=REF_KEY_COLUMNS)
    if result.empty:
        return pd.DataFrame(columns=REF_KEY_COLUMNS + ["cprod"])

    result["npnp_id"] = _to_int(result["npnp_id"])
    result["version"] = _to_int(result["version"])
    result["product_code"] = _compact_product_code(result["product_code"])
    result["cprod"] = result["product_code"]
    return result.dropna(subset=["npnp_id", "version"]).drop_duplicates().sort_values(REF_KEY_COLUMNS).reset_index(drop=True)


def combine_detected_refs(index_refs, histo_refs):
    result = pd.concat([histo_refs, index_refs], ignore_index=True, sort=False)
    if result.empty:
        return pd.DataFrame(columns=REF_KEY_COLUMNS + ["cprod"])
    result["product_code"] = _compact_product_code(result["product_code"])
    result["cprod"] = result["product_code"]
    return result.drop_duplicates().sort_values(REF_KEY_COLUMNS).reset_index(drop=True)


def find_new_refs(detected_refs, ref_master):
    if detected_refs.empty:
        return pd.DataFrame(columns=REF_KEY_COLUMNS + ["cprod"])
    if ref_master.empty:
        return detected_refs.sort_values(REF_KEY_COLUMNS).reset_index(drop=True)

    master = _lower_columns(ref_master)
    master = master.rename(columns={"npnpid": "npnp_id", "prod_code": "product_code"})
    master = master[[column for column in REF_KEY_COLUMNS if column in master.columns]].drop_duplicates()
    master["npnp_id"] = _to_int(master["npnp_id"])
    master["version"] = _to_int(master["version"])
    master["product_code"] = _compact_product_code(master["product_code"])

    merged = detected_refs.merge(master.assign(_already_loaded=True), on=REF_KEY_COLUMNS, how="left")
    return (
        merged[merged["_already_loaded"].isna()]
        .drop(columns=["_already_loaded"])
        .sort_values(REF_KEY_COLUMNS)
        .reset_index(drop=True)
    )


def max_swt_ref_id(ref_master):
    if ref_master.empty:
        return 0
    master = _lower_columns(ref_master)
    if "swt_ref_id" not in master.columns:
        return 0
    values = pd.to_numeric(master["swt_ref_id"], errors="coerce").dropna()
    return int(values.max()) if not values.empty else 0


def build_ref_master_row(ref_row, swt_ref_id, now_value=None):
    now_value = now_value or datetime.now()
    npnp_id = int(ref_row.npnp_id)
    version = int(ref_row.version)
    product_code = str(ref_row.product_code)
    return pd.DataFrame(
        [
            {
                "swt_ref_id": swt_ref_id,
                "npnp_id": npnp_id,
                "version": version,
                "product_code": product_code,
                "swt_ref_fra_datetime": _one_year_ago(now_value),
                "load_file_name": "ACLFTR_sql",
                "comment": f"File-{npnp_id}-{version}-{product_code}- manual load with dm_t_swt_ref.R",
            }
        ]
    )


def build_ref_param_rows(yield_params, analog_params, swt_ref_id, last_ref_param_id):
    yield_df = _lower_columns(yield_params)
    analog_df = _lower_columns(analog_params)
    yield_df["yield_test"] = 1
    analog_df["yield_test"] = 0
    df = pd.concat([yield_df, analog_df], ignore_index=True, sort=False)
    if df.empty:
        return pd.DataFrame(columns=["ref_param_id", "swt_ref_id", "parameter_id", "parameter_name", "yield_test"])

    df = df.drop(columns=[column for column in ["npnpid", "version"] if column in df.columns])
    df["parameter_id"] = pd.to_numeric(df["parameter_id"], errors="coerce")
    df = df.dropna(subset=["parameter_id"]).sort_values("parameter_id").reset_index(drop=True)
    df["parameter_id"] = df["parameter_id"].astype(int)
    df["swt_ref_id"] = int(swt_ref_id)
    df["ref_param_id"] = range(int(last_ref_param_id) + 1, int(last_ref_param_id) + len(df) + 1)
    return df[["ref_param_id", "swt_ref_id", "parameter_id", "parameter_name", "yield_test"]]


def build_yield_rows(ref_params, yield_limits):
    ref_df = _lower_columns(ref_params)
    limits = _lower_columns(yield_limits)
    if ref_df.empty or limits.empty:
        return pd.DataFrame(columns=["ref_param_id", "yield_type", "cal_region", "condition"])
    merged = ref_df.merge(limits, on="parameter_id", how="inner")
    return merged.sort_values("ref_param_id")[["ref_param_id", "yield_type", "cal_region", "condition"]]


def build_analog_rows(ref_params, analog_limits):
    ref_df = _lower_columns(ref_params)
    limits = _lower_columns(analog_limits)
    columns = [
        "ref_param_id",
        "unit",
        "lsl",
        "usl",
        "low_control_limit",
        "high_control_limit",
        "low_cens_limit",
        "high_cens_limit",
    ]
    if ref_df.empty or limits.empty:
        return pd.DataFrame(columns=columns)
    merged = ref_df.merge(limits, on="parameter_id", how="inner")
    return merged.sort_values("ref_param_id")[columns]


def build_new_references(data):
    index_refs = transform_index_refs(data["index_refs"])
    histo_refs = transform_histo_refs(data["histo_refs"])
    detected_refs = combine_detected_refs(index_refs, histo_refs)
    return find_new_refs(detected_refs, data["ref_master"])


def add_swt_ref_ids(new_refs, ref_master):
    if new_refs.empty:
        return new_refs.copy()

    df = new_refs.copy().reset_index(drop=True)
    first_ref_id = max_swt_ref_id(ref_master) + 1
    df["swt_ref_id"] = range(first_ref_id, first_ref_id + len(df))
    return df


def build_reference_payload(reference, parameter_data):
    swt_ref_id = int(reference.swt_ref_id)
    ref_master_row = build_ref_master_row(reference, swt_ref_id)
    ref_param_rows = build_ref_param_rows(
        parameter_data["yield_params"],
        parameter_data["analog_params"],
        swt_ref_id,
        parameter_data["last_param_id"],
    )
    yield_rows = build_yield_rows(parameter_data["ref_params"], parameter_data["yield_limits"])
    analog_rows = build_analog_rows(parameter_data["ref_params"], parameter_data["analog_limits"])

    return {
        "ref_master": ref_master_row,
        "ref_param": ref_param_rows,
        "ref_yield": yield_rows,
        "ref_analog": analog_rows,
    }
