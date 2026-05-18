import logging

import pandas as pd

from extract import extract_dbiltr_param, extract_dbiltr_spec, extract_tpr

logger = logging.getLogger(__name__)
VERSION = "v.3.0-python"


PARAM_COLUMNS = [
    "pcm_ref_id",
    "parameter_id",
    "parameter_name",
    "unit",
    "pcm_group",
    "merge_type",
    "process_option",
    "module",
    "pcell",
    "slm",
    "npnp_id2",
    "parameter_id2",
    "parameter_name2",
    "unit2",
    "reptseq",
    "report_variable",
]

PARAM_COMPARE_COLUMNS = [
    "npnp_id",
    "isis_techno",
    "isis_tpr",
    "parameter_id",
    "parameter_name",
    "unit",
    "pcm_group",
    "merge_type",
    "process_option",
    "module",
    "pcell",
    "slm",
    "npnp_id2",
    "parameter_id2",
    "parameter_name2",
    "unit2",
    "reptseq",
    "report_variable",
]

SPEC_VALUE_COLUMNS = [
    "lsl",
    "usl",
    "low_control_limit",
    "high_control_limit",
    "low_cens_limit",
    "high_cens_limit",
    "lsl3",
    "usl3",
    "target",
    "type",
    "cr",
    "cpk_flag",
]


def _ensure_columns(df, columns):
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = pd.NA
    return result


def _normalize_text(df, columns, default=""):
    result = _ensure_columns(df, columns)
    for column in columns:
        result[column] = result[column].fillna(default).astype(str).str.strip()
    return result


def _normalize_int(series):
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def anti_join(left, right, columns):
    left_work = _ensure_columns(left, columns)
    right_work = _ensure_columns(right, columns)
    keys = right_work[columns].drop_duplicates()
    merged = left_work.merge(keys, on=columns, how="left", indicator=True)
    return merged.loc[merged["_merge"] == "left_only"].drop(columns="_merge")


def build_master_changes(settings, df_prod_npnpid, df_ref_master):
    existing_npnpid = df_ref_master[["npnp_id"]].drop_duplicates()
    new_npnpid = anti_join(df_prod_npnpid, existing_npnpid, ["npnp_id"])

    current_tpr = extract_tpr(settings, existing_npnpid["npnp_id"])
    current_tpr["load_file_name"] = "DBILTR_sql"
    current_tpr["comment"] = (
        current_tpr["isis_techno"].astype(str)
        + " "
        + current_tpr["isis_tpr"].astype(str)
        + " "
        + current_tpr["npnp_id"].astype(str)
        + f" - load with DBILTR_to_datamart_pcm_ref.R version {VERSION}"
    )
    current_tpr["pcm_ref_fra_datetime"] = settings["reference_datetime"]
    current_tpr = current_tpr[
        ["npnp_id", "pcm_ref_fra_datetime", "load_file_name", "comment", "isis_techno", "isis_tpr"]
    ]

    updated_master = anti_join(
        current_tpr,
        df_ref_master,
        ["npnp_id", "isis_techno", "isis_tpr"],
    )
    updated_master = updated_master.merge(
        df_ref_master[["pcm_ref_id", "npnp_id"]].drop_duplicates(),
        on="npnp_id",
        how="inner",
    )
    updated_master = updated_master[
        ["pcm_ref_id", "npnp_id", "pcm_ref_fra_datetime", "load_file_name", "comment", "isis_techno", "isis_tpr"]
    ].drop_duplicates()

    if new_npnpid.empty:
        created_master = pd.DataFrame(
            columns=["npnp_id", "pcm_ref_fra_datetime", "load_file_name", "comment", "isis_techno", "isis_tpr"]
        )
    else:
        created_master = extract_tpr(settings, new_npnpid["npnp_id"])
        created_master["load_file_name"] = "DBILTR_sql"
        created_master["comment"] = (
            created_master["isis_techno"].astype(str)
            + " "
            + created_master["isis_tpr"].astype(str)
            + " "
            + created_master["npnp_id"].astype(str)
            + f" - load with DBILTR_to_datamart_pcm_ref.R version {VERSION}"
        )
        created_master["pcm_ref_fra_datetime"] = settings["reference_datetime"]
        created_master = created_master[
            ["npnp_id", "pcm_ref_fra_datetime", "load_file_name", "comment", "isis_techno", "isis_tpr"]
        ].drop_duplicates()

    return created_master, updated_master


def build_param_changes(settings, df_ref_param):
    text_columns = [
        "parameter_name",
        "unit",
        "pcm_group",
        "merge_type",
        "process_option",
        "module",
        "pcell",
        "slm",
        "npnp_id2",
        "parameter_name2",
        "unit2",
        "report_variable",
    ]
    df_ref_param = _normalize_text(df_ref_param, text_columns)
    ref_master = df_ref_param[["pcm_ref_id", "npnp_id", "isis_techno", "isis_tpr"]].drop_duplicates()

    dbiltr_param = extract_dbiltr_param(settings, ref_master["isis_techno"], ref_master["isis_tpr"])
    dbiltr_param = _normalize_text(dbiltr_param, text_columns)
    dbiltr_param["parameter_id2"] = _normalize_int(dbiltr_param["parameter_id2"])
    dbiltr_param["merge_type"] = dbiltr_param["merge_type"].replace("", pd.NA).fillna("GROUPE")

    param_by_npnp = dbiltr_param.merge(ref_master, on=["isis_techno", "isis_tpr"], how="inner").drop_duplicates()

    new_param = anti_join(
        param_by_npnp,
        df_ref_param,
        ["npnp_id", "isis_techno", "isis_tpr", "parameter_id"],
    )
    new_param = new_param[PARAM_COLUMNS].drop_duplicates()

    param_by_npnp = _normalize_text(param_by_npnp, text_columns)
    df_ref_param = _normalize_text(df_ref_param, text_columns)

    updated_param = anti_join(param_by_npnp, df_ref_param, PARAM_COMPARE_COLUMNS)
    updated_param = updated_param[PARAM_COLUMNS].drop_duplicates()
    updated_param = anti_join(updated_param, new_param, PARAM_COLUMNS)
    updated_param = updated_param.merge(
        df_ref_param[["ref_param_id", "pcm_ref_id", "parameter_id"]].drop_duplicates(),
        on=["pcm_ref_id", "parameter_id"],
        how="inner",
    )
    updated_param = updated_param[["ref_param_id"] + PARAM_COLUMNS].drop_duplicates()

    return new_param, updated_param


def build_spec_changes(settings, df_ref_spec, df_ref_npnp, df_ref_param_lookup, df_ref_spec_lookup):
    df_ref_spec = df_ref_spec.drop_duplicates()
    ref_param = df_ref_spec[["ref_param_id", "parameter_id", "npnp_id", "isis_techno", "isis_tpr"]].drop_duplicates()
    dbiltr_spec = extract_dbiltr_spec(settings, ref_param["isis_techno"], ref_param["isis_tpr"])

    for column in ["parameter_id", "isis_techno", "isis_tpr"]:
        dbiltr_spec[column] = dbiltr_spec[column].astype(str).str.strip()
        df_ref_spec[column] = df_ref_spec[column].astype(str).str.strip()

    dbiltr_spec = dbiltr_spec.merge(
        df_ref_npnp.drop_duplicates(),
        on=["isis_tpr", "isis_techno"],
        how="inner",
    ).drop_duplicates()

    new_key = ["npnp_id", "parameter_id", "isis_techno", "isis_tpr", "version"]
    new_spec = anti_join(dbiltr_spec, df_ref_spec, new_key)
    new_spec = new_spec[
        ["npnp_id", "isis_techno", "isis_tpr", "parameter_id", "version"] + SPEC_VALUE_COLUMNS
    ].drop_duplicates()
    new_spec["parameter_id"] = pd.to_numeric(new_spec["parameter_id"], errors="coerce")
    new_spec = new_spec.merge(
        df_ref_param_lookup.drop_duplicates(),
        on=["isis_techno", "isis_tpr", "npnp_id", "parameter_id"],
        how="left",
    )

    spec_for_compare = dbiltr_spec.copy()
    ref_for_compare = df_ref_spec.copy()
    for frame in [spec_for_compare, ref_for_compare]:
        for column in SPEC_VALUE_COLUMNS:
            if column in ["type", "cpk_flag"]:
                frame[column] = frame[column].fillna("").astype(str).str.strip()
            else:
                frame[column] = frame[column].where(frame[column].notna(), "NULL")

    compare_columns = new_key + SPEC_VALUE_COLUMNS
    updated_spec = anti_join(spec_for_compare, ref_for_compare, compare_columns)
    updated_spec = updated_spec[
        ["npnp_id", "isis_techno", "isis_tpr", "parameter_id", "version"] + SPEC_VALUE_COLUMNS
    ].drop_duplicates()

    new_spec_compare = new_spec.copy()
    for column in SPEC_VALUE_COLUMNS:
        if column in ["type", "cpk_flag"]:
            new_spec_compare[column] = new_spec_compare[column].fillna("").astype(str).str.strip()
        else:
            new_spec_compare[column] = new_spec_compare[column].where(new_spec_compare[column].notna(), "NULL")

    updated_spec = anti_join(
        updated_spec,
        new_spec_compare,
        ["npnp_id", "isis_techno", "isis_tpr", "version"] + SPEC_VALUE_COLUMNS,
    ).drop_duplicates()
    updated_spec = updated_spec.merge(
        df_ref_spec_lookup.drop_duplicates(),
        on=["npnp_id", "isis_techno", "isis_tpr", "parameter_id", "version"],
        how="left",
    )

    updated_spec = updated_spec[["ref_param_version_id", "ref_param_id", "version"] + SPEC_VALUE_COLUMNS].drop_duplicates()
    new_spec = new_spec[["ref_param_id", "version"] + SPEC_VALUE_COLUMNS].drop_duplicates()
    new_spec = new_spec[new_spec["ref_param_id"].notna()]

    return new_spec, updated_spec


def _make_vgroup(df):
    result = df[["ref_param_id", "version", "lsl", "usl", "target"]].drop_duplicates().copy()
    result["s_target"] = result["target"].astype(str)
    result["s_lsl"] = result["lsl"].astype(str)
    result["s_usl"] = result["usl"].astype(str)
    return result[["ref_param_id", "version", "s_target", "s_lsl", "s_usl"]].sort_values(
        ["ref_param_id", "version"]
    )


def _assign_vgroups(df):
    result = df.copy()
    result["s_ref_param_id"] = "R" + result["ref_param_id"].astype(str)
    groups = (
        result[["s_ref_param_id", "s_target", "s_lsl", "s_usl"]]
        .drop_duplicates()
        .sort_values(["s_ref_param_id", "s_lsl", "s_usl", "s_target"])
        .copy()
    )
    groups["vgroup"] = groups.groupby("s_ref_param_id").cumcount() + 1
    result = result.merge(groups, on=["s_ref_param_id", "s_target", "s_lsl", "s_usl"], how="left")
    return result[["vgroup", "ref_param_id", "version", "s_target", "s_lsl", "s_usl"]].drop_duplicates()


def build_vgroup_changes(df_ref_spec_full, df_ref_vgroup):
    vgroup_source = _make_vgroup(df_ref_spec_full.drop_duplicates())
    df_ref_vgroup = df_ref_vgroup.drop_duplicates()

    new_ref_param = anti_join(vgroup_source, df_ref_vgroup, ["ref_param_id"])

    old_ref_param_ids = df_ref_vgroup[["ref_param_id"]].drop_duplicates()
    old_ref_param = vgroup_source.merge(old_ref_param_ids, on="ref_param_id", how="inner")

    new_version = anti_join(old_ref_param, df_ref_vgroup, ["ref_param_id", "version"])
    new_version = anti_join(new_version, new_ref_param, ["ref_param_id", "version", "s_target", "s_lsl", "s_usl"])

    old_versions = df_ref_vgroup[["ref_param_id", "version"]].drop_duplicates()
    old_ref_param_version = old_ref_param.merge(old_versions, on=["ref_param_id", "version"], how="inner")

    updated_limits = anti_join(
        old_ref_param_version,
        df_ref_vgroup,
        ["ref_param_id", "version", "s_target", "s_lsl", "s_usl"],
    )

    new_triplet = anti_join(
        new_version,
        df_ref_vgroup,
        ["ref_param_id", "s_target", "s_lsl", "s_usl"],
    )
    old_triplet = new_version.merge(
        df_ref_vgroup[["ref_param_id", "s_target", "s_lsl", "s_usl"]].drop_duplicates(),
        on=["ref_param_id", "s_target", "s_lsl", "s_usl"],
        how="inner",
    )

    to_delete = pd.concat([new_triplet, updated_limits], ignore_index=True).drop_duplicates()
    delete_ref_param_ids = to_delete[["ref_param_id"]].drop_duplicates()

    rebuild_vgroup = pd.DataFrame(columns=["vgroup", "ref_param_id", "version", "s_target", "s_lsl", "s_usl"])
    if not delete_ref_param_ids.empty:
        previous_for_deleted = delete_ref_param_ids.merge(df_ref_vgroup, on="ref_param_id", how="inner")
        no_limits_previous = previous_for_deleted.drop(columns=["vgroup", "s_target", "s_lsl", "s_usl"])
        no_limits_new = to_delete.drop(columns=["s_target", "s_lsl", "s_usl"])
        all_versions = pd.concat([no_limits_previous, no_limits_new], ignore_index=True).drop_duplicates()

        dbiltr_limits = all_versions.merge(to_delete, on=["ref_param_id", "version"], how="inner")
        missing = anti_join(all_versions, to_delete, ["ref_param_id", "version"])
        missing = missing.merge(
            previous_for_deleted.drop(columns=["vgroup"]),
            on=["ref_param_id", "version"],
            how="inner",
        )
        rebuild_vgroup = _assign_vgroups(pd.concat([dbiltr_limits, missing], ignore_index=True).drop_duplicates())

    new_ref_param_vgroup = _assign_vgroups(new_ref_param) if not new_ref_param.empty else rebuild_vgroup.iloc[0:0]

    current_vgroups = df_ref_vgroup[["vgroup", "ref_param_id", "s_target", "s_lsl", "s_usl"]].drop_duplicates()
    old_triplet = old_triplet.merge(
        current_vgroups,
        on=["ref_param_id", "s_target", "s_lsl", "s_usl"],
        how="left",
    )
    old_triplet = old_triplet[["vgroup", "ref_param_id", "version", "s_target", "s_lsl", "s_usl"]].drop_duplicates()

    return delete_ref_param_ids, rebuild_vgroup, new_ref_param_vgroup, old_triplet
