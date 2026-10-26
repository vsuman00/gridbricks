"""Separate local import commands. Browser routes only read saved snapshots."""

import argparse
import json
from datetime import date
from pathlib import Path

from gridbricks.config import Settings
from gridbricks.ingestion.fixtures import FixtureSource
from gridbricks.ingestion.service import audit, import_scope
from gridbricks.sources.elexon import ElexonSource
from gridbricks.storage.database import migrate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["migrate", "ingest-fixtures", "ingest-sample", "ingest-january", "audit-january"],
    )
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--decision-from", type=date.fromisoformat)
    parser.add_argument("--decision-to", type=date.fromisoformat)
    parser.add_argument("--cutoff", default="09:30")
    args = parser.parse_args(argv)
    if args.command == "audit-january" and (args.decision_from or args.decision_to):
        parser.error(
            "audit-january always covers 1-31 January 2026; decision bounds apply to imports"
        )
    settings = Settings(args.data_dir) if args.data_dir else Settings()
    try:
        if args.command == "migrate":
            migrate(settings)
            result = {"status": "succeeded", "schema": "0001_snapshots"}
        elif args.command == "audit-january":
            result = audit(settings, args.cutoff)
        else:
            full_month = args.command in {"ingest-fixtures", "ingest-january"}
            start = args.decision_from or date(2026, 1, 1 if full_month else 15)
            end = args.decision_to or (date(2026, 1, 31) if full_month else start)
            fixture = args.command == "ingest-fixtures"
            source = FixtureSource() if fixture else ElexonSource()
            try:
                result = import_scope(
                    settings, source, start, end, source_mode="fixture" if fixture else "live"
                )
            finally:
                if not fixture:
                    source.close()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as error:
        # Detailed source outcomes are in the local journal; do not dump source bodies.
        print(json.dumps({"status": "failed", "error": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
