import argparse
import logging
from collections.abc import Iterable, Sequence
from datetime import date, timedelta

from sqlalchemy import bindparam, text

from config import connect_to_dmp


LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
DEFAULT_BATCH_SIZE = 1_000


def get_limits(days_back: int = 1101) -> tuple[int, int, str]:
    limit_date = date.today() - timedelta(days=days_back)
    limit_day = int(limit_date.strftime("%Y%m%d"))
    limit_part = int(limit_date.strftime("%Y%m"))

    if limit_part % 100 != 1:
        part_number = limit_part - 1
    else:
        part_number = limit_part - 100 + 11

    return limit_day, limit_part, f"p{part_number}"


def chunks(values: Sequence[int], size: int) -> Iterable[list[int]]:
    for index in range(0, len(values), size):
        yield list(values[index : index + size])


def validate_partition(partition: str) -> str:
    if not partition.startswith("p") or not partition[1:].isdigit():
        raise ValueError(f"Invalid partition name: {partition}")
    return partition


def fetch_event_ids(connection, queries: Sequence[str], params: dict | None = None) -> list[int]:
    event_ids: set[int] = set()
    for query in queries:
        rows = connection.execute(text(query), params or {})
        for row in rows:
            event_id = row[0]
            if event_id is not None and int(event_id) != 0:
                event_ids.add(int(event_id))
    return sorted(event_ids)


def delete_by_event_ids(
    connection,
    table_names: Sequence[str],
    event_ids: Sequence[int],
    batch_size: int,
    dry_run: bool,
) -> dict[str, int]:
    deleted_rows = {table_name: 0 for table_name in table_names}
    if not event_ids:
        return deleted_rows

    for batch_number, batch_ids in enumerate(chunks(event_ids, batch_size), start=1):
        logging.info("Deleting batch %s (%s event_id)", batch_number, len(batch_ids))
        for table_name in table_names:
            query = (
                text(f"DELETE FROM {table_name} WHERE event_id IN :event_ids")
                .bindparams(bindparam("event_ids", expanding=True))
            )
            if dry_run:
                logging.info("[dry-run] %s: %s event_id", table_name, len(batch_ids))
                continue
            result = connection.execute(query, {"event_ids": batch_ids})
            deleted_rows[table_name] += result.rowcount or 0

    return deleted_rows


def clean_section(
    connection,
    label: str,
    queries: Sequence[str],
    delete_tables: Sequence[str],
    params: dict | None = None,
    limit: int | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> None:
    event_ids = fetch_event_ids(connection, queries, params)
    if limit is not None:
        event_ids = event_ids[:limit]

    logging.info("%s: %s event_id to clean", label, len(event_ids))
    if not event_ids:
        return

    deleted_rows = delete_by_event_ids(
        connection=connection,
        table_names=delete_tables,
        event_ids=event_ids,
        batch_size=batch_size,
        dry_run=dry_run,
    )
    for table_name, row_count in deleted_rows.items():
        logging.info("%s: %s row(s) deleted from %s", label, row_count, table_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean old DMP events.")
    parser.add_argument("--days-back", type=int, default=1101)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    limit_day, limit_part, partition = get_limits(args.days_back)
    partition = validate_partition(partition)

    logging.info("limit_day=%s", limit_day)
    logging.info("limit_part=%s", limit_part)
    logging.info("partition=%s", partition)

    engine = connect_to_dmp()
    params = {"limit_day": limit_day, "limit_part": limit_part}

    # Keep the R script behavior close: each statement is committed by the DB
    # instead of holding one very large transaction for the whole cleanup.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        clean_section(
            connection=connection,
            label="dcs_id 1",
            queries=[
                """
                SELECT DISTINCT we.event_id
                FROM (t_event e RIGHT JOIN t_lot_event we ON e.event_id = we.event_id)
                RIGHT JOIN t_pcm_lot sw ON sw.event_id = we.event_id
                WHERE we.ref_calendar_id < :limit_day
                """,
                """
                SELECT DISTINCT sw.event_id
                FROM (t_event e RIGHT JOIN t_lot_event we ON e.event_id = we.event_id)
                LEFT JOIN t_pcm_lot sw ON sw.event_id = we.event_id
                WHERE we.ref_calendar_id < :limit_day
                  AND e.dcs_id = 1
                """,
            ],
            delete_tables=["t_pcm_lot", "t_lot_event", "t_lot_path", "t_event"],
            params=params,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        clean_section(
            connection=connection,
            label="dcs_id 2",
            queries=[
                """
                SELECT DISTINCT sw.event_id
                FROM (t_event e RIGHT JOIN t_lot_event we ON e.event_id = we.event_id)
                RIGHT JOIN t_mes_lot sw ON sw.event_id = we.event_id
                WHERE we.ref_calendar_id < :limit_day
                """,
                """
                SELECT DISTINCT sw.event_id
                FROM (t_event e RIGHT JOIN t_lot_event we ON e.event_id = we.event_id)
                LEFT JOIN t_mes_lot sw ON sw.event_id = we.event_id
                WHERE we.ref_calendar_id < :limit_day
                  AND e.dcs_id = 2
                """,
            ],
            delete_tables=["t_mes_lot", "t_lot_event", "t_lot_path", "t_event"],
            params=params,
            limit=50_000,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        clean_section(
            connection=connection,
            label="dcs_id 3",
            queries=[
                """
                SELECT DISTINCT sw.event_id
                FROM (t_event e RIGHT JOIN t_lot_event we ON e.event_id = we.event_id)
                RIGHT JOIN t_swt_lot_main sw ON sw.event_id = we.event_id
                WHERE we.ref_calendar_id < :limit_day
                """,
                """
                SELECT DISTINCT sw.event_id
                FROM (t_event e RIGHT JOIN t_lot_event we ON e.event_id = we.event_id)
                LEFT JOIN t_swt_lot_main sw ON sw.event_id = we.event_id
                WHERE we.ref_calendar_id < :limit_day
                  AND e.dcs_id = 3
                """,
            ],
            delete_tables=["t_swt_lot_main", "t_lot_event", "t_lot_path", "t_event"],
            params=params,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        clean_section(
            connection=connection,
            label="dcs_id 4",
            queries=[
                """
                SELECT DISTINCT sw.event_id
                FROM (t_event e RIGHT JOIN t_wafer_event we ON e.event_id = we.event_id)
                RIGHT JOIN t_swt_waf_main sw ON sw.event_id = we.event_id
                WHERE we.ref_calendar_id < :limit_day
                """,
                """
                SELECT DISTINCT sw.event_id
                FROM (t_event e RIGHT JOIN t_wafer_event we ON e.event_id = we.event_id)
                LEFT JOIN t_swt_waf_main sw ON sw.event_id = we.event_id
                WHERE we.ref_calendar_id < :limit_day
                  AND e.dcs_id = 4
                """,
            ],
            delete_tables=[
                "t_swt_waf_main",
                "t_lot_event",
                "t_wafer_event",
                "t_lot_path",
                "t_wafer_path",
                "t_event",
            ],
            params=params,
            limit=10_000,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        clean_section(
            connection=connection,
            label="dcs_id 5",
            queries=[
                """
                SELECT DISTINCT sw.event_id
                FROM (t_event e RIGHT JOIN t_wafer_event we ON e.event_id = we.event_id)
                LEFT JOIN t_swt_die_main sw ON sw.event_id = we.event_id
                WHERE sw.part_month < :limit_part
                """,
                f"""
                SELECT DISTINCT sw.event_id
                FROM t_swt_die_main PARTITION ({partition}) sw
                LEFT JOIN t_wafer_event we ON we.event_id = sw.event_id
                WHERE sw.part_month < :limit_part
                """,
            ],
            delete_tables=[
                f"t_swt_die_main PARTITION ({partition})",
                "t_lot_event",
                "t_wafer_event",
                "t_lot_path",
                "t_wafer_path",
                "t_event",
            ],
            params=params,
            limit=5_000,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        clean_section(
            connection=connection,
            label="dcs_id 6",
            queries=[
                """
                SELECT DISTINCT sw.event_id
                FROM (t_event e RIGHT JOIN t_wafer_event we ON e.event_id = we.event_id)
                LEFT JOIN t_pcm_waf sw ON sw.event_id = we.event_id
                WHERE sw.part_month < :limit_part
                """,
                f"""
                SELECT DISTINCT sw.event_id
                FROM t_pcm_waf PARTITION ({partition}) sw
                LEFT JOIN t_wafer_event we ON we.event_id = sw.event_id
                WHERE sw.part_month < :limit_part
                """,
            ],
            delete_tables=[
                f"t_pcm_waf PARTITION ({partition})",
                "t_lot_event",
                "t_wafer_event",
                "t_lot_path",
                "t_wafer_path",
                "t_event",
            ],
            params=params,
            limit=10_000,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        clean_section(
            connection=connection,
            label="dcs_id 7",
            queries=[f"SELECT DISTINCT event_id FROM t_pcm_ret PARTITION ({partition})"],
            delete_tables=[
                f"t_pcm_ret PARTITION ({partition})",
                "t_lot_event",
                "t_wafer_event",
                "t_lot_path",
                "t_wafer_path",
                "t_event",
            ],
            limit=5_000,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        clean_section(
            connection=connection,
            label="dcs_id 12",
            queries=[f"SELECT DISTINCT event_id FROM t_fdc_ref_path_ret PARTITION ({partition})"],
            delete_tables=[
                f"t_fdc_wafer_path PARTITION ({partition})",
                "t_lot_event",
                "t_wafer_event",
                "t_lot_path",
                "t_wafer_path",
                "t_event",
            ],
            limit=10_000,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
