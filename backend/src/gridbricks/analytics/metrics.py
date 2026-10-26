import math
from collections import Counter


def metrics(rows: list[dict]) -> dict:
    errors = [row["error_mw"] for row in rows if row["state"] == "matched"]
    if not errors:
        return {"mae_mw": None, "rmse_mw": None, "bias_mw": None}
    if not all(error is not None and math.isfinite(error) for error in errors):
        raise ValueError("Matched errors must be finite")
    count = len(errors)
    return {
        "mae_mw": math.fsum(abs(error) / count for error in errors),
        "rmse_mw": math.hypot(*errors) / math.sqrt(count),
        "bias_mw": math.fsum(error / count for error in errors),
    }


def summarize(rows: list[dict], accuracy: bool = True) -> dict:
    reasons = dict(sorted(Counter(row["state"] for row in rows).items()))
    result = {
        "expected_count": len(rows),
        "forecast_selected_count": sum(row["forecast_mw"] is not None for row in rows),
        "reason_counts": reasons,
    }
    if accuracy:
        matched = sum(row["state"] == "matched" for row in rows)
        result.update(
            complete_actual_count=sum(row.get("actual_mw") is not None for row in rows),
            matched_count=matched,
            matched_fraction=matched / len(rows) if rows else 0.0,
        )
    return result
