# Source research and open decisions

Date: 26 October 2026. Status: read-only reconnaissance, not full source-contract validation or a January accuracy study.

Implementation follow-up: [T01 source-contract findings](T01_SOURCE_CONTRACT.md) resolve or leave open Q01-Q07 explicitly, record eight new live checks and specify future deterministic fixtures. The original audits below are preserved unchanged. T01 remains PARTIAL, and interval-average alignment remains unavailable.

## 1. Evidence register

| ID | Source | What it supports | Limits |
| --- | --- | --- | --- |
| S01 | [WINDFOR stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) | Dataset specified by the assignment | The documentation page's static HTML required JavaScript; parameters were checked through S03 and live requests |
| S02 | [FUELHH stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) | Actual dataset specified by the assignment | Same static-page limitation as S01 |
| S03 | [Elexon official OpenAPI schema](https://data.elexon.co.uk/swagger/v1/swagger.json) | Available parameters, response fields, error statuses; FUELHH average MW over half-hours; mutually exclusive filter families | Schema and endpoint access can change; it does not establish every WINDFOR physical interval convention |
| S04 | [Elexon wind generation explanation](https://bmrs.elexon.co.uk/wind-generation) | Hourly wind forecasts and operational-metering coverage; outturn comparison context | Hourly cadence alone is not proof that each value is an average over the following hour |
| S05 | [Elexon generation by fuel type explanation](https://bmrs.elexon.co.uk/generation-by-fuel-type) | Outturn omits embedded generation and farms outside operational metering | Do not generalize this series to all UK wind or a utility portfolio |
| S06 | [Elexon wind forecast endpoint explanation](https://bmrs.elexon.co.uk/api-documentation/endpoint/forecast/generation/wind/latest) | Metering scope and described update schedule | This is a research reference, not a replacement ingestion endpoint; do not use latest-only selection for replay |
| S07 | [Nord Pool 2020 N2EX timing announcement](https://www.nordpoolgroup.com/en/message-center-container/newsroom/exchange-message-list/2020/q4/nord-pool-announces-gb-auction-changes-for-brexit/) | Historical example of a specific GB auction deadline | Announces 09:50 GMT from January 2021; does not establish the client's auction, January 2026 rules, or internal cutoff |

Only S01/S02 data enters analytical calculations. Other sources explain definitions and market context; no prices, weather, demand, or alternative generation series are added.

## 2. Checks performed in this workspace

Two live stream requests used the publication window 2026-01-15T00:00:00Z to 2026-01-16T00:00:00Z. Results and exact request URLs are preserved in [sample audit](evidence/elexon-sample-audit.json). The [API contract audit](evidence/elexon-api-contract-audit.json) records selected official-schema fields and the full response hash.

| Check | Observation | Implication |
| --- | --- | --- |
| WINDFOR response | 584 records across eight publication timestamps in that request window | Multiple vintages must be retained; this is not 584 independent forecast targets |
| WINDFOR latest sampled publication | 73 distinct target timestamps with 60-minute spacing | Source forecasts are hourly in this sample; validate other dates and physical interval meaning |
| FUELHH response | 980 records before filtering, 49 WIND rows after filtering | Client-side WIND validation is required even if a server filter is used |
| FUELHH sample target times | 22:30, 23:00, 23:30 on 15 January | Half-hour target spacing is consistent with S03 |
| FUELHH source definition | Average power in MW for each half-hour | These are power values, not already MWh |
| WINDFOR supported query | Publication lower/upper bounds | Omitting filters requests the latest publication and cannot recreate an arbitrary historical cutoff |
| FUELHH supported query | Publication bounds or settlement-date bounds; optional fuel filter | Do not combine the two bound families |
| Boundary behavior | Sample includes a publication at 16 January 00:00 | Avoid assuming an exclusive server upper bound; overfetch, deduplicate, and enforce local bounds |

One WINDFOR sample published on 15 January at 22:30 targets 14 January at 21:00. Publication time and target time must therefore be filtered independently. Do not assume all records in a forecast response describe future delivery relative to their publication.

The sample contains actual publication times such as 07:30 and 09:30 rather than just the schedule described on the explanatory page. Do not rewrite source timestamps to fit a schedule or choose a forecast using a nominal release hour. Use each actual `publishTime` field.

These counts describe a publication-window sample, including boundaries, not complete 15 January delivery coverage. They do not establish the 16 January target day's completeness, finality of actuals, January error metrics, or the absence of revisions. Response hashes identify the inspected bytes; future downloads may legitimately differ.

## 3. Reproduce the source reconnaissance

Run from the repository root with Python 3 and internet access. This code is read-only and does not require the future application or external Python packages. It fetches the same window, prints counts and examples, and lists source-schema parameters. It intentionally does not claim to validate comparison semantics.

```bash
python3 - <<'PY'
import json
from urllib.parse import urlencode
from urllib.request import urlopen

base = "https://data.elexon.co.uk/bmrs/api/v1/datasets/"
query = urlencode({
    "publishDateTimeFrom": "2026-01-15T00:00:00Z",
    "publishDateTimeTo": "2026-01-16T00:00:00Z",
})
for dataset in ("WINDFOR", "FUELHH"):
    with urlopen(base + dataset + "/stream?" + query, timeout=20) as response:
        rows = json.load(response)
    selected = [r for r in rows if dataset != "FUELHH" or r.get("fuelType") == "WIND"]
    print(dataset, "total:", len(rows), "relevant:", len(selected))
    print(json.dumps(selected[:2], indent=2))

with urlopen("https://data.elexon.co.uk/swagger/v1/swagger.json", timeout=20) as response:
    spec = json.load(response)
for path, operation in spec["paths"].items():
    if path.lower() in ("/datasets/windfor/stream", "/datasets/fuelhh/stream"):
        print(path, [p["name"] for p in operation["get"]["parameters"]])
PY
```

Network failures must be reported as failed source checks. Do not rewrite the saved evidence to make it appear successful or interpret a failed request as zero generation.

## 4. Questions to resolve during T01

| ID | Question | Current baseline | Required evidence or handling |
| --- | --- | --- | --- |
| Q01 | Does January refer to decision or delivery dates? | Decision dates, as worded in the assignment | Keep assumption visible; revise shared configuration if assessor clarifies |
| Q02 | Which auction and internal deadline applies? | Configurable 09:30 local demo assumption | Client/assessor information if available; historical S07 is context only |
| Q03 | Does each WINDFOR value represent an hourly interval average, a point, or another definition? | Unresolved; proposed hourly-average alignment is conditional | Find an explicit primary definition or document the justified comparison policy; do not infer from spacing |
| Q04 | Are source query endpoints inclusive and how are late actual revisions retrieved? | Boundary overlap is handled locally | Inspect adjacent windows and the final delivery period using the official parameter families |
| Q05 | How much earlier history is sufficient for each cutoff? | Initial seven-day lookback; bounds recorded | Check coverage for first decision and earlier publications; extend or flag bounded search exhaustion |
| Q06 | Are there same-target/publication conflicts or changing cadences across the month? | Retain and expose conflicts | Full import audit plus fixtures; no insertion-order tie-break |
| Q07 | What reference does FUELHH actual mean for this assignment? | Latest unambiguous outturn in the selected snapshot | Retain source scope and revisions; do not label final settlement truth |

Q01/Q02 have explicit workable defaults and do not require a new permission step for setup. Q03 is an analytical dependency: full accuracy cannot be claimed until the comparison policy is defensible and consistently documented. Domain research may proceed alongside setup, but proposed alignment is not verified implementation.

## 5. Domain distinctions to preserve

- Publication time: when the source says a forecast was published; not proof of receipt by a trading system.
- Target time: delivery interval or timestamp to which a value applies, according to the verified source definition.
- Decision cutoff: simulated buying deadline used to select forecast vintages.
- Retrieval time: when this application downloaded source data, which is much later than January in this historical assignment.
- Actual reference: retrospective outturn selected within a pinned snapshot; not information supplied to the historical decision view.
- Error sign: forecast minus actual. Positive errors indicate overforecast wind, not necessarily the client's realized financial loss.

No claim has been established about a complete January import, quantified accuracy, recommended purchases, saved cost, runtime behavior, production readiness, or client approval.
