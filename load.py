import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)


def _sql_clean(df):
    return df.replace("NULL", None).where(df.notna(), None)


def append_table(engine, table_name, df):
    if df.empty:
        logger.info("No insert for %s", table_name)
        return 0
    clean_df = _sql_clean(df)
    clean_df.to_sql(table_name, engine, if_exists="append", index=False, method="multi")
    logger.info("Inserted %s row(s) into %s", len(df), table_name)
    return len(df)


def execute_updates(engine, statement, rows, label):
    if rows.empty:
        logger.info("No update for %s", label)
        return 0
    payload = _sql_clean(rows).to_dict("records")
    with engine.begin() as conn:
        conn.execute(text(statement), payload)
    logger.info("Updated %s row(s) for %s", len(payload), label)
    return len(payload)


def delete_vgroups(engine, df):
    if df.empty:
        logger.info("No vgroup delete")
        return 0
    payload = _sql_clean(df).to_dict("records")
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM t_pcm_ref_vgroup WHERE ref_param_id = :ref_param_id"),
            payload,
        )
    logger.info("Deleted vgroups for %s ref_param_id value(s)", len(payload))
    return len(payload)


def load_master(engine, results):
    inserted = append_table(engine, "t_pcm_ref_master", results["created_master"])
    updated = execute_updates(
        engine,
        """
        UPDATE t_pcm_ref_master
        SET
            pcm_ref_fra_datetime = :pcm_ref_fra_datetime,
            load_file_name = :load_file_name,
            comment = :comment,
            isis_techno = :isis_techno,
            isis_tpr = :isis_tpr
        WHERE pcm_ref_id = :pcm_ref_id
        AND npnp_id = :npnp_id
        """,
        results["updated_master"],
        "t_pcm_ref_master",
    )
    return inserted, updated


def load_param(engine, results):
    inserted = append_table(engine, "t_pcm_ref_param", results["new_param"])
    updated = execute_updates(
        engine,
        """
        UPDATE t_pcm_ref_param
        SET
            parameter_name = :parameter_name,
            unit = :unit,
            pcm_group = :pcm_group,
            merge_type = :merge_type,
            process_option = :process_option,
            module = :module,
            pcell = :pcell,
            slm = :slm,
            npnp_id2 = :npnp_id2,
            parameter_id2 = :parameter_id2,
            parameter_name2 = :parameter_name2,
            unit2 = :unit2,
            reptseq = :reptseq,
            report_variable = :report_variable
        WHERE ref_param_id = :ref_param_id
        AND pcm_ref_id = :pcm_ref_id
        AND parameter_id = :parameter_id
        """,
        results["updated_param"],
        "t_pcm_ref_param",
    )
    return inserted, updated


def load_spec(engine, results):
    inserted = append_table(engine, "t_pcm_ref_spec", results["new_spec"])
    updated = execute_updates(
        engine,
        """
        UPDATE t_pcm_ref_spec
        SET
            lsl = :lsl,
            usl = :usl,
            low_control_limit = :low_control_limit,
            high_control_limit = :high_control_limit,
            low_cens_limit = :low_cens_limit,
            high_cens_limit = :high_cens_limit,
            lsl3 = :lsl3,
            usl3 = :usl3,
            target = :target,
            type = :type,
            cr = :cr,
            cpk_flag = :cpk_flag
        WHERE ref_param_version_id = :ref_param_version_id
        AND ref_param_id = :ref_param_id
        AND version = :version
        """,
        results["updated_spec"],
        "t_pcm_ref_spec",
    )
    return inserted, updated


def load_vgroup(engine, results):
    deleted = delete_vgroups(engine, results["delete_vgroup_ids"])
    rebuilt = append_table(engine, "t_pcm_ref_vgroup", results["rebuild_vgroup"])
    new_refs = append_table(engine, "t_pcm_ref_vgroup", results["new_vgroup"])
    old_triplets = append_table(engine, "t_pcm_ref_vgroup", results["old_triplet_vgroup"])
    return {
        "deleted": deleted,
        "rebuilt": rebuilt,
        "new_refs": new_refs,
        "old_triplets": old_triplets,
    }
