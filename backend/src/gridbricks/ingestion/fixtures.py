"""Deterministic synthetic demo inputs; these are never Elexon observations."""

import json
from datetime import date, datetime, timedelta

from gridbricks.sources.elexon import request_url


class FixtureSource:
    def fetch(self, dataset, parameters):
        rows = []
        if dataset == "WINDFOR":
            publication_day = date.fromisoformat(parameters["publishDateTimeFrom"][:10])
            for ahead in (1, 2):
                delivery = publication_day + timedelta(days=ahead)
                for hour in range(24):
                    if delivery == date(2026, 1, 21) and hour == 5:
                        continue
                    base = 100 + delivery.day * 7 + hour * 9
                    for clock, delta in (("08:30", 0), ("09:30", 5), ("10:30", 40)):
                        if hour == 0 and clock == "09:30":
                            continue
                        value = (
                            100
                            if hour == 0 and clock == "08:30"
                            else 140
                            if hour == 0
                            else base + delta
                        )
                        row = {
                            "dataset": dataset,
                            "startTime": f"{delivery}T{hour:02}:00:00Z",
                            "publishTime": f"{publication_day}T{clock}:00Z",
                            "generation": value,
                        }
                        rows.append(row)
                        if delivery == date(2026, 1, 16) and hour == 3 and clock == "09:30":
                            rows.append({**row, "generation": value + 1})
            rows.append(dict(rows[0]))  # Exact duplicate retains two raw-row lineage entries.
        else:
            delivery = date.fromisoformat(parameters["settlementDateFrom"])
            for half in range(48):
                if delivery == date(2026, 1, 21) and half == 12:
                    continue
                start = datetime.fromisoformat(f"{delivery}T00:00:00+00:00") + timedelta(
                    minutes=half * 30
                )
                row = {
                    "dataset": dataset,
                    "fuelType": "WIND",
                    "startTime": start.isoformat().replace("+00:00", "Z"),
                    "publishTime": (start + timedelta(minutes=30))
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "generation": 0 if half == 0 else 90 + delivery.day * 7 + (half // 2) * 9,
                    "settlementDate": str(delivery),
                    "settlementPeriod": half + 1,
                }
                rows.append(row)
                if half == 4:
                    rows.append(
                        {
                            **row,
                            "publishTime": f"{delivery}T23:59:00Z",
                            "generation": row["generation"] + 2,
                        }
                    )
        return (
            "fixture://synthetic/" + request_url(dataset, parameters).split("datasets/")[1],
            (json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()),
            200,
        )
