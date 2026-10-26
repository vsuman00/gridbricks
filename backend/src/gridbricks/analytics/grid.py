from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("A source timestamp must include its UTC offset")
    return parsed.astimezone(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def target_grid(decision_date: str, cutoff: str) -> list[dict]:
    decision = date.fromisoformat(decision_date)
    delivery = decision + timedelta(days=1)
    hour, minute = map(int, cutoff.split(":"))
    deadline = datetime.combine(decision, time(hour, minute), LONDON).astimezone(UTC)
    target = datetime.combine(delivery, time(), LONDON).astimezone(UTC)
    end = datetime.combine(delivery + timedelta(days=1), time(), LONDON).astimezone(UTC)
    rows = []
    while target < end:
        rows.append(
            {
                "decision_date": decision_date,
                "cutoff_utc": iso(deadline),
                "target_start": iso(target),
                "target_end": iso(target + timedelta(hours=1)),
            }
        )
        target += timedelta(hours=1)
    return rows
