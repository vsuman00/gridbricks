# Client walkthrough: historical wind forecast review

Proposed length: 6 minutes. Audience: UK utility buying and operations reviewers. Use the local application with the saved live January snapshot, not preview mode. Show the snapshot ID in Data details before discussing numbers.

| Time | Screen or action | Message |
| --- | --- | --- |
| 0:00-0:45 | Decision view; January date and 09:30 cutoff | This replays what the public national wind forecast said before each configured buying deadline. The cutoff is a demo assumption, not a confirmed client auction rule. |
| 0:45-2:00 | Set decision date to 15 January, cutoff to 09:00; inspect the 16 January 00:00 row and publication | The stored source selects 7,398 MW, published at 07:30, for this target. Publication and target times are separate. |
| 2:00-2:45 | Change cutoff to 09:30, apply; inspect the same row | The selected forecast becomes 7,472 MW from the 09:30 publication. Across that delivery day, all 24 selected target values change. Later publications remain excluded from either replay. |
| 2:45-4:10 | Switch to Accuracy and set the full 1-31 January decision range | The saved snapshot has 744 matched hourly targets at the 09:30 cutoff. The timestamp-reference benchmark has MAE 1,995.57 MW, RMSE 2,498.82 MW, and mean bias +1,727.98 MW. Positive bias means forecast above the selected reference on average. Actuals and error are retrospective; they were not known at the buying time. |
| 4:10-5:10 | Open a row's source records, then Export CSV | The row shows the chosen publication, exact-time actual constituent, and raw response lineage. CSV and charts use the same snapshot and policies; missing values would stay missing. |
| 5:10-6:00 | Read the orange comparison note and coverage | WINDFOR's physical averaging interval has not been established. We compare each hourly target with the FUELHH half-hour average starting at that timestamp. The national series and this benchmark do not determine a client purchase quantity, energy volume, or financial saving. |

## Demonstration setup

Run `make backend-dev` and `make frontend-dev` after `make setup` and `make ingest-january`. Open `http://127.0.0.1:5173`. If offline, use `make ingest-fixtures` and run the backend with `GRIDBRICKS_DATA_DIR="$PWD/data/fixtures"`; label all fixture numbers synthetic and do not use the live values above.

## Questions to invite

- What is the team's real buying cutoff, timezone and approval workflow? The 09:30 setting is configurable but unconfirmed.
- Would reviewers prefer another physical comparison basis after Elexon clarifies WINDFOR interval meaning? A new named policy and snapshot would be required.
- Which historical source revision archive is authoritative for the business? This snapshot contains revisions returned during its bounded retrieval; it does not prove exhaustive historical publication capture or final settlement truth.
