import pandas as pd
from sqlalchemy import text

from transform import clean_text_columns


def load_created_reference(df_created_reference, dmp_engine):
    if df_created_reference.empty:
        return

    with dmp_engine.begin() as connection:
        df_created_reference.to_sql(
            "t_mes_ref_oper",
            connection,
            if_exists="append",
            index=False,
            method="multi",
        )


def load_updated_reference(df_updated_reference, dmp_engine):
    if df_updated_reference.empty:
        return

    df_updated_reference = clean_text_columns(
        df_updated_reference, ["proccard_label", "operation_label", "gate_label"]
    )
    update_stmt = text(
        """
        UPDATE t_mes_ref_oper
        SET proccard_label = :proccard_label,
            gate_label = :gate_label,
            operation_label = :operation_label,
            gate_in_seq = :gate_in_seq
        WHERE proccard = :proccard
          AND gate = :gate
          AND operation = :operation
          AND route = :route
        """
    )
    params = [
        {
            "proccard": row.proccard,
            "proccard_label": row.proccard_label,
            "gate": row.gate,
            "gate_label": row.gate_label,
            "operation": row.operation,
            "operation_label": row.operation_label,
            "gate_in_seq": None if pd.isna(row.gate_in_seq) else row.gate_in_seq,
            "route": row.route,
        }
        for row in df_updated_reference.itertuples(index=False)
    ]

    with dmp_engine.begin() as connection:
        connection.execute(update_stmt, params)
