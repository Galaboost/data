from pathlib import Path

import pandas as pd


ACTIVE_TECHNOS = ("AH018", "C11N", "XH018", "XR013", "XT011", "XT018")

TECHNO_DIRECTORIES = {
    "AH018": "FWT_AH18",
    "C10N": "FWT_C10",
    "C11N": "FWT_C11",
    "T18AL": "FWT_SOI",
    "T18B": "FWT_T18B",
    "T18RF": "FWT_T18RF",
    "T18SO": "FWT_SOI",
    "XH018": "FWT_XH018",
    "XP018": "FWT_XP018",
    "XR013": "FWT_XR013",
    "XT011": "FWT_XT011",
    "XT018": "FWT_XT018",
}

NPARAM_BY_TECHNO = {
    "T18RF": (
        "10691,10692,10693,10595,10596,10597,10598,10599,10000,"
        "10001,10002,10003,10004,10005,10006,10007,10008,10009,10015,10017,"
        "10026,10027,10028,10029,10030,10037,10063,10064,10072,10074,10080,10327"
    ),
    "XH018": (
        "10691,10695,10696,10697,10698,10699,10000,"
        "10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,"
        "10011,10012,10013,10014,10015,10016,10017,10018,10019,10020,"
        "10021,10022,10023,10024,10025,10026,10027,10028,10029,10030,"
        "10031,10032,10033,10034,10035,10036,10037,10038,10039,10040,"
        "10041,10042,10043,10044,10045,10046,10047,10048,10049,10050,"
        "10051,10052,10053,10054,10055,10056,10057,10058,10059,10060"
    ),
    "XT018": (
        "10691,10695,10696,10697,10698,10699,10000,"
        "10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,"
        "10011,10012,10013,10014,10015,10016,10017,10018,10019,10020,"
        "10021,10022,10023,10024,10025,10026,10027,10028,10029,10030,"
        "10031,10032,10033,10034,10035,10036,10037,10038,10039,10040,"
        "10041,10042,10043,10044,10045,10046,10047,10048,10049,10050,"
        "10051,10052,10053,10054,10055,10056,10057,10058,10059,10060"
    ),
    "AH018": (
        "10691,10695,10696,10697,10698,10699,"
        "10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,"
        "10011,10012,10013,10014,10015,10016,10017,10018,10019,10020,"
        "10021,10022,10023,10024,10025,10026,10027,10028,10029,10030,"
        "10031,10032,10033,10034,10035,10036,10037,10038,10039,10040,"
        "10041,10042,10043,10044,10045,10046,10047,10048,10049,10050,"
        "10051,10052,10053,10054,10055,10056,10057,10058,10059,10060,"
        "10061,10062,10063,10064,10065,10066,10067,10068,10069,10070,"
        "10099"
    ),
    "XP018": (
        "10691,10695,10696,10697,10698,10699,"
        "10001,10002,10003,10004,10005,10006,10007,10008,10009,"
        "10010,10011,10012,10013,10015,10016,10017,10018,10019,10021,"
        "10022,10025,10026,10028,10029,10032,10033,10035,10036,10057,10058,"
        "10060,10062,10063,10064,10099"
    ),
    "XR013": "10691,10695,10696,10697,10698,10699,10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,10032,10035",
}

DEFAULT_NPARAM = (
    "10691,10695,10696,10697,10698,10699,10000,"
    "10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,"
    "10011,10012,10013,10014,10015,10016,10017,10018,10019,10020,"
    "10021,10022,10023,10024,10025,10026,10027,10028,10029,10030,"
    "10031,10032,10033,10034,10035,10036,10037,10038,10039,10040,"
    "10041,10042,10043,10044,10045,10046,10047,10048,10049,10050"
)


def prepare_profiles(raw_profiles, active_technos=ACTIVE_TECHNOS):
    if raw_profiles.empty:
        return pd.DataFrame(columns=["techno", "npnpid", "version"])

    df = raw_profiles.copy()
    df["techno"] = df["profile_name"].astype(str).str.extract(r"([A-Za-z0-9]*)", expand=False)
    df = df.rename(columns={"selected_npnpid": "npnpid", "selected_version": "version"})
    df = df[["techno", "npnpid", "version"]].drop_duplicates()
    df["npnpid"] = df["npnpid"].map(format_identifier)
    df["version"] = df["version"].map(format_identifier)
    df = df[df["techno"].isin(active_technos)]
    return df.sort_values(["techno", "npnpid", "version"]).reset_index(drop=True)


def get_archive_directory(techno, root_directory):
    try:
        directory = TECHNO_DIRECTORIES[str(techno)]
    except KeyError as exc:
        raise ValueError(f"Techno repository not defined: {techno}") from exc
    return Path(root_directory) / directory


def get_pmax(techno):
    return 10000 if str(techno) == "T18SO" else 12000


def get_predefined_nparams(techno):
    values = NPARAM_BY_TECHNO.get(str(techno), DEFAULT_NPARAM)
    return [value.strip() for value in values.split(",") if value.strip()]


def build_nparam_list(techno, extracted_nparams=None):
    if str(techno) == "T18SO" and extracted_nparams is not None:
        column = _first_existing(extracted_nparams, "NPARAM", "nparam")
        return [format_identifier(value) for value in extracted_nparams[column].dropna()]
    return get_predefined_nparams(techno)


def combine_measurements(parametric, yield_data):
    frames = [frame for frame in (parametric, yield_data) if frame is not None and not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def transform_swt_measurements(measurements, pmax, id_columns):
    if measurements.empty:
        return pd.DataFrame()

    df = _uppercase_columns(measurements)
    required = {"NLOCFAB", "DDTEST", "NPNPID", "VERSION", "NPARAM", "VALUE", "TPARAM"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing SWT measurement columns: {sorted(missing)}")

    for column in ["NLOCFAB", "NTRANCH", "NPNPID", "VERSION", "TPARAM"]:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()

    nparam_numeric = pd.to_numeric(df["NPARAM"], errors="coerce")
    clean_tparam = df["TPARAM"].astype("string").str.replace(" ", "", regex=False).str.strip()
    df["TPARAM"] = clean_tparam.where(
        nparam_numeric >= int(pmax),
        "t" + df["NPARAM"].astype("string").str.strip() + "_" + clean_tparam,
    )

    df["DDTEST"] = normalize_ddtest(df["DDTEST"])
    df = df.sort_values("TPARAM")
    pivot = (
        df.pivot_table(
            index=id_columns,
            columns="TPARAM",
            values="VALUE",
            aggfunc="first",
            dropna=False,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    return pivot


def merge_archive(existing_archive, fresh_data, group_columns):
    if fresh_data.empty:
        return existing_archive.copy() if existing_archive is not None else fresh_data

    frames = []
    if existing_archive is not None and not existing_archive.empty:
        archive = _normalize_core_columns(existing_archive)
        if "DDTEST" in archive.columns:
            archive["DDTEST"] = normalize_ddtest(archive["DDTEST"])
        frames.append(archive)
    frames.append(_normalize_core_columns(fresh_data))

    df = pd.concat(frames, ignore_index=True, sort=False).drop_duplicates()
    df["DDTEST"] = normalize_ddtest(df["DDTEST"])
    df = df.sort_values(["DDTEST", *group_columns])
    max_dates = df.groupby(group_columns, dropna=False)["DDTEST"].transform("max")
    df = df[df["DDTEST"] == max_dates]
    return df.sort_values(["DDTEST", *group_columns]).reset_index(drop=True)


def build_allgood_wafer(wafer_archive):
    df = _normalize_core_columns(wafer_archive)
    allgood_column = _first_existing_case_insensitive(df, "AllGood")
    columns = ["NPNPID", "DDTEST", "NLOCFAB", "NTRANCH", allgood_column]
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing AllGood wafer columns: {missing}")
    return df[columns].rename(columns={allgood_column: "AllGood"})


def format_identifier(value):
    if pd.isna(value):
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value).strip()
    if numeric.is_integer():
        return str(int(numeric))
    return str(value).strip()


def normalize_ddtest(series):
    values = series.astype("string").str.strip()
    parsed = pd.to_datetime(values, errors="coerce", dayfirst=False)
    parsed_dayfirst = pd.to_datetime(values, errors="coerce", dayfirst=True)
    parsed = parsed.fillna(parsed_dayfirst)
    return parsed.dt.strftime("%Y-%m-%d").fillna(values)


def _uppercase_columns(df):
    output = df.copy()
    output.columns = [str(column).upper() for column in output.columns]
    return output


def _normalize_core_columns(df):
    core_columns = {
        "nlocfab": "NLOCFAB",
        "ntranch": "NTRANCH",
        "ddtest": "DDTEST",
        "npnpid": "NPNPID",
        "version": "VERSION",
        "nparam": "NPARAM",
        "value": "VALUE",
        "tparam": "TPARAM",
    }
    output = df.copy()
    output = output.rename(columns={column: core_columns.get(str(column).lower(), column) for column in output.columns})
    return output


def _first_existing(df, *columns):
    for column in columns:
        if column in df.columns:
            return column
    raise KeyError(f"Missing expected column among {columns}")


def _first_existing_case_insensitive(df, name):
    target = str(name).lower()
    for column in df.columns:
        if str(column).lower() == target:
            return column
    raise KeyError(f"Missing expected column: {name}")
