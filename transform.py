import pandas as pd

from config import (
    DIE_COLUMNS,
    EMAP_COLUMNS,
    MASKSET_ALIASES,
    RET_COLUMNS,
)


EMAP_KEYS = {
    "SAPN__",
    "DESIGN",
    "XFRAME",
    "YFRAME",
    "SHOTSX",
    "SHOTSY",
    "COLALL",
    "ROWALL",
    "CXSIZE",
    "CYSIZE",
    "REFMTX",
    "REFMTY",
}

RET_MAP_KEYS = {f"MAP{i:03d}" for i in range(1, 100)}
DIE_MAP_KEYS = {f"MAP{i:03d}" for i in range(1, 1000)}


def _first_existing(df, *names):
    for name in names:
        if name in df.columns:
            return name
    raise KeyError(f"Missing expected column among {names}")


def _trim_numeric(value, kind="float"):
    if pd.isna(value):
        return pd.NA
    value = str(value)[:9]
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return pd.NA
    if kind == "int":
        return int(parsed)
    return float(parsed)


def _to_numeric(series, kind="float"):
    return series.map(lambda value: _trim_numeric(value, kind=kind))


def _map_number(name, prefix_len=3):
    return int(str(name)[prefix_len:7])


def prepare_devices(df_devices, limit):
    if df_devices.empty:
        return df_devices.copy()

    df = df_devices.iloc[::-1].reset_index(drop=True)
    if "customer_name" in df.columns:
        df = df[df["customer_name"] != "ALEDIA"]
    if "process_family" in df.columns:
        df = df[df["process_family"] != "SL011"]
    return df.head(limit).reset_index(drop=True)


def normalize_maskset(maskset_name):
    return MASKSET_ALIASES.get(str(maskset_name), str(maskset_name))


def parse_map0_file(map0_file):
    rows = []
    for raw_line in str(map0_file or "").splitlines():
        parts = raw_line.split()
        if not parts:
            continue
        row = {"variable": parts[0], "value": parts[1] if len(parts) > 1 else pd.NA}
        for index, part in enumerate(parts[:14], start=1):
            row[f"V{index}"] = part
        rows.append(row)
    return pd.DataFrame(rows)


def _pivot_records(df_lines, keys, start_key):
    filtered = df_lines[df_lines["variable"].isin(keys)][["variable", "value"]].copy()
    if filtered.empty:
        return pd.DataFrame()

    ids = []
    current_id = 0
    for variable in filtered["variable"]:
        if not ids or variable == start_key:
            current_id += 1
        ids.append(current_id)
    filtered["Id"] = ids
    return (
        filtered.pivot_table(
            index="Id",
            columns="variable",
            values="value",
            aggfunc="first",
            dropna=False,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )


def build_emap_ascii(map_lines, device_row):
    df = _pivot_records(map_lines, EMAP_KEYS, "SAPN__")
    if df.empty:
        return pd.DataFrame(columns=EMAP_COLUMNS)

    if {"SHOTSX", "SHOTSY"}.issubset(df.columns):
        df = df[
            (pd.to_numeric(df["SHOTSX"], errors="coerce") > 1)
            & (pd.to_numeric(df["SHOTSY"], errors="coerce") > 1)
        ]
    df = df.drop_duplicates()
    df["ret_x_max"] = df["SHOTSX"]
    df["ret_y_max"] = df["SHOTSY"]

    df = df.rename(
        columns={
            "COLALL": "die_x_max",
            "ROWALL": "die_y_max",
            "XFRAME": "ret_x_size",
            "YFRAME": "ret_y_size",
            "CXSIZE": "die_x_size",
            "CYSIZE": "die_y_size",
            "DESIGN": "maskset_name",
            "REFMTX": "swt_die_x_offset",
            "REFMTY": "swt_die_y_offset",
            "SAPN__": "sapn",
        }
    )

    for column in ["ret_x_size", "ret_y_size", "die_x_size", "die_y_size"]:
        df[column] = _to_numeric(df[column])
    for column in ["die_x_max", "die_y_max", "ret_x_max", "ret_y_max"]:
        df[column] = _to_numeric(df[column], kind="int")

    df["ret_y_vs_x_ratio"] = df["ret_y_size"] / df["ret_x_size"]
    df["die_y_vs_x_ratio"] = df["die_y_size"] / df["die_x_size"]
    df["swt_die_x_offset"] = _to_numeric(df["swt_die_x_offset"], kind="int") - 1
    df["swt_die_y_offset"] = _to_numeric(df["swt_die_y_offset"], kind="int") - 1

    device = pd.DataFrame([device_row.to_dict()])
    merged = df.merge(device, on="maskset_name", how="right")
    drop_columns = [
        "Id",
        "process_family",
        "local_process_family",
        "customer_proj_name",
        "customer_id",
        "global_process_id",
        "customer_name",
        "module_list",
        "device_type",
        "emap_id",
    ]
    merged = merged.drop(columns=[column for column in drop_columns if column in merged.columns])
    merged = merged.drop_duplicates()
    merged["filename"] = "Unknown"
    return merged


def build_emap_total(emap_ascii, map0_info):
    if emap_ascii.empty:
        return pd.DataFrame(columns=EMAP_COLUMNS)

    info = map0_info.copy()
    merged = emap_ascii.merge(
        info,
        left_on=["sapn", "maskset_name"],
        right_on=["SAPN", "DESIGN"],
        how="left",
    )
    merged = merged.drop(
        columns=[
            column
            for column in ["SAPN", "DESIGN", "MAP_TYPE", "COLCNT", "ROWCNT", "XDIES", "YDIES", "COMMENT", "MAJ_DATE"]
            if column in merged.columns
        ]
    )
    merged = merged.rename(
        columns={
            "VERSION": "version",
            "CHIP_COUNT": "die_qty",
            "DT_EFFET": "effective_fra_datetime",
        }
    )
    merged["filename"] = (
        merged["device_id"].astype(str)
        + "_"
        + merged["sapn"].astype(str)
        + "_"
        + merged["maskset_name"].astype(str)
        + "_"
        + merged["version"].astype(str)
    )
    merged = merged[merged["sapn"].notna()]
    return merged.reindex(columns=EMAP_COLUMNS)


def _map_rows(map_lines, keys, start_key="DESIGN", unique=True, filter_shots=False):
    df = _pivot_records(map_lines, keys, start_key)
    if df.empty:
        return df
    if filter_shots and {"SHOTSX", "SHOTSY"}.issubset(df.columns):
        df = df[
            (pd.to_numeric(df["SHOTSX"], errors="coerce") > 1)
            & (pd.to_numeric(df["SHOTSY"], errors="coerce") > 1)
        ]
    if unique:
        df = df.drop_duplicates()
    return df


def build_ret_emap(map_lines, emap_total):
    keys = {"DESIGN", "YFRAME", "XFRAME", "SHOTSY", "SHOTSX"} | RET_MAP_KEYS
    id_cols = ["Id", "DESIGN", "SHOTSX", "SHOTSY", "XFRAME", "YFRAME"]
    merge_left = ["DESIGN", "SHOTSX", "SHOTSY", "ret_x_size", "ret_y_size", "ret_y_vs_x_ratio"]
    merge_right = ["maskset_name", "ret_x_max", "ret_y_max", "ret_x_size", "ret_y_size", "ret_y_vs_x_ratio"]
    df_input = _map_rows(
        map_lines,
        keys,
        unique=True,
        filter_shots=True,
    )
    rows = []
    for _, record in df_input.iterrows():
        for column, value in record.items():
            if column in id_cols or pd.isna(value):
                continue
            if not str(column).startswith("MAP"):
                continue
            ret_y = int(float(record["SHOTSY"])) - _map_number(column, prefix_len=3) + 1
            for ret_x, ret_type in enumerate(str(value), start=1):
                row = {column_name: record[column_name] for column_name in id_cols if column_name != "Id"}
                row.update(
                    {
                        "ret_y": ret_y,
                        "ret_x_size": _trim_numeric(record["XFRAME"]),
                        "ret_y_size": _trim_numeric(record["YFRAME"]),
                        "ret_x": ret_x,
                        "ret_type": ret_type,
                    }
                )
                row["ret_y_vs_x_ratio"] = row["ret_y_size"] / row["ret_x_size"]
                rows.append(row)

    df_ret_xy = pd.DataFrame(rows)
    if df_ret_xy.empty:
        return pd.DataFrame()

    merged = df_ret_xy.merge(
        emap_total,
        left_on=merge_left,
        right_on=merge_right,
        how="right",
    )
    merged["center_mm_distance"] = pd.NA
    merged = merged[merged["ret_x"].notna()].copy()
    merged["id"] = range(1, len(merged) + 1)
    return merged


def _die_map_lines(map_lines):
    keys = (
        {"DESIGN", "YFRAME", "XFRAME", "SHOTSY", "SHOTSX", "CYSIZE", "CXSIZE", "COLALL", "ROWALL"}
        | DIE_MAP_KEYS
    )
    return _map_rows(
        map_lines,
        keys,
        unique=True,
        filter_shots=True,
    )


def _build_die_line_rows(map_lines):
    df_input = _die_map_lines(map_lines)
    rows = []
    for _, record in df_input.iterrows():
        for column, value in record.items():
            if column in {"Id", "COLALL", "CXSIZE", "CYSIZE", "DESIGN", "ROWALL", "SHOTSX", "SHOTSY", "XFRAME", "YFRAME"}:
                continue
            if pd.isna(value) or not str(column).startswith("MAP"):
                continue
            die_y = int(float(record["ROWALL"])) - _map_number(column, prefix_len=3) + 1
            row = {
                "COLALL": record["COLALL"],
                "CXSIZE": record["CXSIZE"],
                "CYSIZE": record["CYSIZE"],
                "DESIGN": record["DESIGN"],
                "ROWALL": record["ROWALL"],
                "SHOTSX": record.get("SHOTSX"),
                "SHOTSY": record.get("SHOTSY"),
                "XFRAME": record["XFRAME"],
                "YFRAME": record["YFRAME"],
                "die_y": die_y,
                "value": str(value),
                "die_x_size": _trim_numeric(record["CXSIZE"]),
                "die_y_size": _trim_numeric(record["CYSIZE"]),
            }
            row["die_y_vs_x_ratio"] = row["die_y_size"] / row["die_x_size"]
            rows.append(row)
    return pd.DataFrame(rows)


def build_die_ret_emap(map_lines, ret_emap):
    df_die = _build_die_line_rows(map_lines)
    rows = []
    for _, record in df_die.iterrows():
        for die_x, die_type in enumerate(str(record["value"]), start=1):
            row = record.drop(labels=["value"]).to_dict()
            row["die_x"] = die_x
            row["die_type"] = die_type
            rows.append(row)

    df_die_xy = pd.DataFrame(rows)
    if df_die_xy.empty:
        return pd.DataFrame()

    df_die_xy["Modulo_x"] = (df_die_xy["COLALL"].astype(int) // df_die_xy["SHOTSX"].astype(int)).astype(int)
    df_die_xy["Modulo_y"] = (df_die_xy["ROWALL"].astype(int) // df_die_xy["SHOTSY"].astype(int)).astype(int)
    df_die_xy["die_x_ret_position"] = ((df_die_xy["die_x"].astype(int) - 1) % df_die_xy["Modulo_x"]) + 1
    df_die_xy["die_y_ret_position"] = ((df_die_xy["die_y"].astype(int) - 1) % df_die_xy["Modulo_y"]) + 1

    df_die_xy["ret_x"] = ((df_die_xy["die_x"].astype(int) - 1) // df_die_xy["Modulo_x"]) + 1
    df_die_xy["ret_y"] = ((df_die_xy["die_y"].astype(int) - 1) // df_die_xy["Modulo_y"]) + 1

    merge_left = ["DESIGN", "SHOTSX", "SHOTSY", "die_x_size", "die_y_size", "die_y_vs_x_ratio", "ret_x", "ret_y"]
    merge_right = ["DESIGN", "SHOTSX", "SHOTSY", "die_x_size", "die_y_size", "die_y_vs_x_ratio", "ret_x", "ret_y"]
    merged = df_die_xy.merge(ret_emap, left_on=merge_left, right_on=merge_right, how="inner")
    merged["center_mm_distance"] = pd.NA
    return merged


def classify_partial_reticles(ret_emap, die_ret_emap):
    ret = ret_emap.copy()
    dies = die_ret_emap.copy()
    if ret.empty or dies.empty:
        ret["test_ret_type"] = pd.NA
        return ret

    ret["ret_type"] = ret["ret_type"].astype(str).str.strip().str[:2]
    dies["die_type"] = dies["die_type"].astype(str).str.strip().str[:2]

    ret["Xcenter"] = ((pd.to_numeric(ret["SHOTSX"], errors="coerce") + 1) // 2).astype("Int64")
    ret["Ycenter"] = ((pd.to_numeric(ret["SHOTSY"], errors="coerce") + 1) // 2).astype("Int64")

    center = ret[(ret["ret_x"].astype(int) == ret["Xcenter"].astype(int)) & (ret["ret_y"].astype(int) == ret["Ycenter"].astype(int))]
    center_id = center["id"].iloc[0] if not center.empty else pd.NA
    reference = dies[dies["id"] == center_id].sort_values(["die_x_ret_position", "die_y_ret_position"])

    def edges(frame):
        if frame.empty:
            return (), (), (), ()
        return (
            tuple(frame[frame["die_x_ret_position"] == frame["die_x_ret_position"].min()]["die_type"]),
            tuple(frame[frame["die_y_ret_position"] == frame["die_y_ret_position"].min()]["die_type"]),
            tuple(frame[frame["die_x_ret_position"] == frame["die_x_ret_position"].max()]["die_type"]),
            tuple(frame[frame["die_y_ret_position"] == frame["die_y_ret_position"].max()]["die_type"]),
        )

    reference_edges = edges(reference)
    test_values = []
    ret_types = []
    for _, row in ret.iterrows():
        ret_type = row["ret_type"]
        test_ret_type = pd.NA

        if ret_type in {".", "L", "E", "M"}:
            test_ret_type = "."
        if ret_type == "C":
            current = dies[dies["id"] == row["id"]].sort_values(["die_x_ret_position", "die_y_ret_position"])
            test_ret_type = "C" if edges(current) == reference_edges else "P"

        test_values.append(test_ret_type)
        ret_types.append(ret_type)

    ret["test_ret_type"] = test_values
    ret["ret_type"] = ret_types
    return ret


def build_device_payload(device_row, maps_rows, map0_info):
    maskset_name = str(device_row["maskset_name"])
    if maps_rows.empty:
        raise ValueError(f"No map0_header row found for {maskset_name}")
    map_file_column = _first_existing(maps_rows, "MAP0_FILE", "map0_file")

    map_file_content = "\n".join(
        maps_rows[map_file_column].dropna().astype(str).tolist()
    )
    map_lines = parse_map0_file(map_file_content)
    emap_ascii = build_emap_ascii(map_lines, device_row)
    emap_total = build_emap_total(emap_ascii, map0_info)
    ret_emap = build_ret_emap(map_lines, emap_total)
    die_ret_emap = build_die_ret_emap(map_lines, ret_emap)
    ret_emap = classify_partial_reticles(ret_emap, die_ret_emap)

    return {
        "emap": emap_total.reindex(columns=EMAP_COLUMNS),
        "ret_emap": ret_emap,
        "die_ret_emap": die_ret_emap,
    }


def build_t_ret(ret_emap, t_emap):
    merged = t_emap.merge(
        ret_emap,
        left_on=["sapn", "maskset_name", "device_id", "version"],
        right_on=["sapn", "DESIGN", "device_id", "version"],
        how="inner",
    )
    return merged.reindex(columns=RET_COLUMNS)


def build_t_die(die_ret_emap, t_emap, t_ret):
    emap_ret = t_ret.merge(t_emap, on="emap_id", how="left")
    merged = emap_ret.merge(
        die_ret_emap,
        left_on=["sapn", "maskset_name", "device_id", "version", "ret_x", "ret_y"],
        right_on=["sapn", "DESIGN", "device_id", "version", "ret_x", "ret_y"],
        how="inner",
    )
    return merged.reindex(columns=DIE_COLUMNS)


def build_ret_update_rows(existing_rets, t_ret):
    return existing_rets.merge(
        t_ret,
        on=["emap_id", "ret_x", "ret_y", "ret_type", "center_mm_distance"],
        how="inner",
    )


def should_skip_device(device_row):
    return pd.isna(device_row.get("maskset_name"))


def normalize_device_row(device_row):
    data = device_row.copy()
    data["maskset_name"] = normalize_maskset(data["maskset_name"])
    return data
