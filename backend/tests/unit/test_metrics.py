import json
import math
from pathlib import Path

import pytest

from gridbricks.analytics.metrics import metrics, summarize


def row(error, state="matched", forecast=100, actual=80):
    return {
        "state": state,
        "forecast_mw": forecast,
        "actual_mw": actual,
        "error_mw": error,
    }


def test_known_values_have_twenty_mw_absolute_error_and_zero_bias():
    fixture = json.loads(
        (Path(__file__).parents[1] / "fixtures/metrics_known_values.json").read_text()
    )
    values = [
        row(forecast - actual, forecast=forecast, actual=actual)
        for forecast, actual in zip(
            fixture["forecast_mw"], fixture["actual_reference_mw"], strict=True
        )
    ]
    assert metrics(values) == fixture["expected"]


def test_empty_or_all_missing_results_have_null_metrics():
    expected = {"mae_mw": None, "rmse_mw": None, "bias_mw": None}
    assert metrics([]) == expected
    assert (
        metrics([row(None, "missing_forecast", None), row(None, "missing_actual", actual=None)])
        == expected
    )


def test_single_zero_generation_match_is_included():
    values = [row(0, forecast=0, actual=0)]
    assert metrics(values) == {"mae_mw": 0.0, "rmse_mw": 0.0, "bias_mw": 0.0}
    coverage = summarize(values, accuracy=True)
    assert coverage["matched_count"] == 1
    assert coverage["matched_fraction"] == 1.0


def test_whole_range_metrics_pool_observations_instead_of_daily_cards():
    values = [row(100)] + [row(0) for _ in range(9)]
    result = metrics(values)
    assert result["mae_mw"] == 10
    assert result["bias_mw"] == 10
    assert result["rmse_mw"] == pytest.approx(math.sqrt(1000))


def test_coverage_primary_reasons_reconcile_to_the_full_expected_grid():
    values = [
        row(20),
        row(None, "forecast_conflict", None, 100),
        row(None, "missing_actual", 100, None),
        row(None, "missing_forecast", None, None),
    ]
    coverage = summarize(values, accuracy=True)
    assert coverage["expected_count"] == 4
    assert coverage["forecast_selected_count"] == 2
    assert coverage["complete_actual_count"] == 2
    assert coverage["matched_count"] == 1
    assert coverage["matched_fraction"] == 0.25
    assert sum(coverage["reason_counts"].values()) == 4
    assert coverage["reason_counts"] == {
        "matched": 1,
        "forecast_conflict": 1,
        "missing_actual": 1,
        "missing_forecast": 1,
    }


def test_no_expected_rows_has_zero_coverage_without_division_failure():
    coverage = summarize([], accuracy=True)
    assert coverage["expected_count"] == 0
    assert coverage["matched_count"] == 0
    assert coverage["matched_fraction"] == 0
