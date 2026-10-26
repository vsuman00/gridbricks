# ADR-003: Single-container Vercel assignment delivery

Status: Accepted for the assignment package on 27 October 2026. Local image behavior is verified; Vercel production behavior is not yet verified.

## Context

The challenge requires Docker and a public sample app on Vercel or Heroku. The existing development workflow runs Vite and FastAPI separately and stores a historical January snapshot in an ignored local directory. Browser requests already read stored data and must never start an Elexon import.

## Decision

Use one root `Dockerfile.vercel`. A Node build stage creates the React output; a Python 3.12 stage installs the locked backend and serves that output beside the existing `/api/v1` routes from one FastAPI process on `$PORT`. The public Host list comes from Vercel's generated/production URL environment values or an explicit custom-domain setting. Local development keeps the two-server loopback workflow.

Package the reviewed live January SQLite database, manifest and saved raw responses under `deployment/data/`. The build checks database integrity, the expected snapshot/input identity and all raw hashes. Runtime reads use SQLite `mode=ro`, an unprivileged container user and files without write permission. An updated source snapshot requires a new checked artifact and deployment. The import CLI remains outside HTTP requests.

The public repository and live-data UI include the required attribution and link to the [Elexon BMRS open data licence](https://www.elexon.co.uk/bsc/data/balancing-mechanism-reporting-agent/copyright-licence-bmrs-data/). Synthetic fixture views are labelled separately.

## Consequences and limits

The single-port image avoids a frontend/backend cross-origin split and satisfies the assignment's Docker requirement. It also keeps API, UI, CSV and source lineage tied to the same packaged snapshot. Docker image and browser checks passed locally; no Vercel project or hosted URL has been validated yet. This choice does not provide persistent refreshes, authentication, rate limiting or a multi-user service guarantee. The analytical comparison policy from ADR-002 is unchanged.
