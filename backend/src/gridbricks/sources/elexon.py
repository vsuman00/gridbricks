"""Fixed-host Elexon source access with bounded retries and no latest shortcut."""

import secrets
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

import httpx

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets/"


class SourceError(RuntimeError):
    pass


def request_url(dataset, parameters):
    if dataset not in {"WINDFOR", "FUELHH"}:
        raise ValueError("Unsupported analytical dataset")
    expected = (
        {"publishDateTimeFrom", "publishDateTimeTo"}
        if dataset == "WINDFOR"
        else {"settlementDateFrom", "settlementDateTo", "fuelType"}
    )
    if set(parameters) != expected or (dataset == "FUELHH" and parameters["fuelType"] != "WIND"):
        raise ValueError("Explicit supported history filters are required")
    return BASE_URL + dataset + "/stream?" + urlencode(sorted(parameters.items()))


class ElexonSource:
    """At most 3 x 20-second requests plus 10 seconds total retry delay per window."""

    def __init__(self, client=None, sleep=time.sleep, jitter=None):
        self._owns_client = client is None
        self.client = (
            client if client is not None else httpx.Client(timeout=20.0, follow_redirects=False)
        )
        self.sleep = sleep
        self.jitter = jitter if jitter is not None else lambda: secrets.randbelow(251) / 1000
        self.last_attempt_count = 0

    def close(self):
        if self._owns_client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def fetch(self, dataset, parameters):
        url = request_url(dataset, parameters)
        delay_budget = 10.0
        self.last_attempt_count = 0
        for attempt in range(3):
            self.last_attempt_count = attempt + 1
            response = None
            try:
                response = self.client.get(url, timeout=20.0)
                if response.status_code == 200:
                    return url, response.content, response.status_code
                if response.status_code != 429 and not 500 <= response.status_code <= 599:
                    raise SourceError(f"source_http_{response.status_code}")
            except httpx.TransportError:
                pass
            if attempt == 2:
                raise SourceError("source_retry_exhausted")
            delay = 2**attempt + self.jitter()
            if response is not None and response.headers.get("Retry-After"):
                retry_after = response.headers["Retry-After"]
                try:
                    delay = max(0.0, float(retry_after))
                except ValueError:
                    try:
                        delay = max(
                            0.0,
                            (
                                parsedate_to_datetime(retry_after) - datetime.now(UTC)
                            ).total_seconds(),
                        )
                    except (ValueError, TypeError):
                        pass
            if delay > delay_budget:
                raise SourceError("source_retry_budget_exceeded")
            delay_budget -= delay
            self.sleep(delay)
        raise SourceError("source_retry_exhausted")
