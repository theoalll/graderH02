# IP Addressing Grader (BGN / Packet Tracer)

A reusable, web-based grader for computer-networks IP-addressing assignments
(VLSM/FLSM allocation + DHCP topology in Cisco Packet Tracer). The teaching
assistant authors a **case**; a student uploads a **.pkt** file; the system
decodes it, solves the expected addressing, and grades the submission.

## Architecture

```
backend/
  ptdecoder/        Vendored + patched Packet Tracer decoder (Twofish-EAX)
  app/
    schemas.py      Pydantic models: CaseSchema, StudentJSON, SolveResult, GradeReport
    engine/         vars (NPM -> X/NPM3), formulas (safe evaluator), vlsm, solver
    adapter.py      ptdecoder document -> normalized StudentJSON
    grader/         bucket (IP -> subnet), checks, score (90-pt auto scale)
    main.py         FastAPI: /api/parse-pkt, /api/solve, /api/grade
  tests/            solver + decoder tests, bgn_case.json fixture
```

## Decoder notes (ptdecoder fork)

The vendored `ptdecoder` was patched for Packet Tracer **8.2.2** files:

1. **`ref_id` / connections** — PT 8.x stores the reference id as a child
   `<SAVE_REF_ID>` element (not a `DEVICE` attribute), so cables could not be
   resolved. Now captured → `connections` resolve.
2. **Notes** — `<NOTE>` lives inside `PHYSICALWORKSPACE`, which was in the
   heavy-skip list. Removed from the skip set (its heavy children are still
   skipped individually) → identity + subnet-label notes are captured.
3. **Model** — device `model` attribute captured from `ENGINE/TYPE`.
4. **Port matching** — connection resolution falls back to a trailing port
   index (e.g. `FastEthernet0/1` -> interface #1) when names don't match.

> **Known limitation:** DHCP pools are only read from the router CLI
> `running-config`. Pools configured via Packet Tracer's GUI are **not**
> captured — require students to use CLI `ip dhcp pool` (documented in the
> assignment brief).

## Run (Docker — recommended)

```bash
cp .env.example .env        # set APP_USERNAME / APP_PASSWORD
docker compose up --build
# App served on host port 30004 (login with the credentials above)
# backend API -> http://localhost:30004/api/...
```

The frontend (nginx) proxies `/api/*` to the backend. Cases are persisted in
**PostgreSQL** (see `DATABASE_URL` in `docker-compose.yml`); grading is
ephemeral (nothing saved). From inside the container the host Postgres is reached
via `host.docker.internal` (`extra_hosts`), authenticated by password (pg_hba
already permits the 172.16.0.0/12 Docker subnet with md5).

### Reverse proxy / public exposure
A Cloudflare Tunnel ingress routes `grader-h02.teyyow.web.id` -> `http://localhost:30004`
(config in `/etc/cloudflared/config.yml`). The matching DNS CNAME was created with
`cloudflared tunnel route dns <uuid> grader-h02.teyyow.web.id`.

## Run (local backend only, for development)

```bash
cd backend
pip install -r requirements.txt
DATABASE_URL=postgresql://graderh02:change_me@localhost:5432/graderh02 \
  uvicorn app.main:app --reload
```

Auth: all API routes except `GET /` and `POST /api/login` require a Bearer token
obtained from `/api/login` (single shared TA credential from env).

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | health |
| POST | `/api/parse-pkt` | upload `.pkt` → normalized `StudentJSON` |
| POST | `/api/solve` | `{case, npm}` → expected answer-key table |
| POST | `/api/grade` | multipart `{case(json), npm, file(.pkt)}` → `GradeReport` |
| POST | `/api/grade-json` | `{case, npm, student}` → `GradeReport` (testing) |

Example (solve the bundled BGN case for NPM 2406123456):

```bash
curl -F "case=@tests/bgn_case.json;type=application/json" \
     -F "npm=2406123456" \
     -F "file=@/path/to/student.pkt" \
     http://localhost:8000/api/grade
```

## Scoring

Auto-graded portion = **90 pts** (50 allocation + 40 implementation): per-subnet
checks `device_counts`, `ip_in_subnet`, `gateway`, `dhcp_pool`, `links_up`.
The 10-pt analysis section and the visual items (`note_name_npm`,
`palette_boxes`, `device_labels`, `wireless_dots`) are surfaced as a **manual**
checklist for the TA.

## Tests

```bash
cd backend && python3 -m pytest -q
```
