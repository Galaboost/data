import pandas as pd


FINAL_COLUMNS = [
    "proccard",
    "proccard_label",
    "gate",
    "gate_label",
    "operation",
    "operation_label",
    "gate_in_seq",
    "route",
]

TEXT_REPLACEMENTS = {
    "\xa0": " ",
    "<a0>": " ",
    "\xe9": " ",
    "<e9>": "e",
    "\xc9": " ",
    "<c9>": "e",
    "\xb5": " ",
    "<b5>": "e",
    "\xf4": " ",
    "<f4>": "e",
    "\xd4": " ",
    "<d4>": "e",
    "\xb0": " ",
    "<b0>": "e",
    "\xe0": " ",
    "<e0>": "e",
    "\xFC\xBE\x8E\x86\x94\xBC": "e",
    "'": " ",
}


def clean_text_value(value):
    if pd.isna(value):
        return value

    cleaned = str(value)
    for old, new in TEXT_REPLACEMENTS.items():
        cleaned = cleaned.replace(old, new)
    return cleaned


def clean_text_columns(df, columns):
    cleaned = df.copy()
    for column in columns:
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].map(clean_text_value)
    return cleaned


def build_symaro_reference(data):
    pco = data["proccard"].merge(
        data["proccardoper"], left_on="PCA_ID", right_on="PCO_PCARD_ID", how="left"
    )
    pco = pco.merge(data["oper"], left_on="PCO_OPERATION_ID", right_on="OPE_ID", how="left")
    pcr = pco.merge(data["routepcard"], left_on="PCA_ID", right_on="RTE_PCARD_ID", how="left")
    pcr = pcr.merge(data["route"], left_on="RTE_ROUTE_ID", right_on="RTE_ID", how="left")
    final = pcr.merge(data["gate"], left_on="PCA_GATE_ID", right_on="GATE_ID", how="left")

    return final[
        [
            "PCA_NAME",
            "PCA_COMMENT",
            "GATE_NAME",
            "PCA_GATE_COMMENT",
            "OPE_NAME",
            "OPE_COMMENT",
            "RTE_NAME",
            "PCO_SEQUENCE",
        ]
    ].drop_duplicates()


def normalize_symaro_reference(df_route_from_symaro):
    symaro = df_route_from_symaro.rename(
        columns={
            "PCA_NAME": "proccard",
            "PCA_COMMENT": "proccard_label_symaro",
            "GATE_NAME": "gate",
            "PCA_GATE_COMMENT": "gate_label_symaro",
            "OPE_NAME": "operation",
            "OPE_COMMENT": "operation_label_symaro",
            "RTE_NAME": "route",
            "PCO_SEQUENCE": "gate_in_seq_symaro",
        }
    ).copy()

    symaro = clean_text_columns(
        symaro,
        ["proccard_label_symaro", "gate_label_symaro", "operation_label_symaro"],
    )
    symaro.loc[symaro["proccard"].eq("EAUMRWK"), "proccard_label_symaro"] = (
        "Casse de tranches"
    )
    return symaro.drop_duplicates()


def format_delta_frame(df):
    return pd.DataFrame(
        {
            "proccard": df["proccard"],
            "proccard_label": df["proccard_label_symaro"],
            "gate": df["gate"],
            "gate_label": df["gate_label_symaro"],
            "operation": df["operation"],
            "operation_label": df["operation_label_symaro"],
            "gate_in_seq": df["gate_in_seq_symaro"],
            "route": df["route"],
        }
    ).drop_duplicates()


def build_reference_delta(df_from_datamart, df_route_from_symaro):
    symaro = normalize_symaro_reference(df_route_from_symaro)
    reference = symaro.merge(
        df_from_datamart,
        on=["proccard", "gate", "operation", "route"],
        how="left",
    )

    created = reference[reference["operation_label"].isna()].copy()
    created = created[created["route"].notna()].drop_duplicates()
    created = format_delta_frame(created)
    created["operation_label"] = created["operation_label"].fillna("").astype(str).str.strip()

    existing = reference[reference["operation_label"].notna()].drop_duplicates().copy()
    changed = (
        existing["proccard_label"].ne(existing["proccard_label_symaro"])
        | existing["gate_label"].ne(existing["gate_label_symaro"])
        | existing["gate_in_seq"].ne(existing["gate_in_seq_symaro"])
        | existing["operation_label"].ne(existing["operation_label_symaro"])
    )
    updated = format_delta_frame(existing.loc[changed].copy())

    return created, updated
