# IP Addressing Grader

A web app for grading Cisco Packet Tracer IP-addressing labs (VLSM/FLSM
allocation plus DHCP and gateway configuration). A teaching assistant authors a
**case**; a student uploads a **.pkt** file; the app decodes it, solves the
expected addressing for that student's NPM, and grades the submission.

Grading is ephemeral: cases and device types are stored, results are not.

## How a submission is graded

1. The TA picks a case, enters the student NPM, and uploads the `.pkt` file.
2. The decoder reads the file into a normalized topology.
3. The solver resolves the case variables from the NPM, runs VLSM over the base
   block, and produces the expected addressing.
4. The grader compares each subnet and each expected device against the
   submission and returns a score with a per-check report.

## Architecture

```
backend/
  ptdecoder/      Vendored and patched Packet Tracer decoder (Twofish-EAX)
  app/
    schemas.py    Pydantic models: CaseSchema, StudentJSON, SolveResult, GradeReport
    engine/       vars (NPM to X/NPM3), formulas (safe evaluator), vlsm, solver
    adapter.py    ptdecoder document to normalized StudentJSON
    grader/       per-subnet checks and per-device scoring
    auth.py       shared TA credential, bearer tokens
    cases_store.py, master_store.py   PostgreSQL storage
    main.py       FastAPI routes
  seed/           Bundled cases and device types, loaded on startup
  tests/          solver, grader, and decoder tests

frontend/
  src/pages/      Login, Cases, CaseBuilder, Submit
  src/components/ ExpectedTable, GradeReport, PrefixRecommendation, DeviceTypeManager
  src/theme.tsx   light and dark theme, light by default, stored per browser
  src/toast.tsx   toast notifications
  src/styles.css  design tokens and component styles
```

## Run with Docker

```bash
cp .env.example .env        # set APP_USERNAME and APP_PASSWORD
docker compose up --build
```

The app is served on host port `30004`. The example env sets the username to
`admin` and a placeholder password, so change the password before deploying.
The frontend (nginx) proxies `/api/*` to the backend.

Cases are stored in PostgreSQL. `docker-compose.yml` defaults `DATABASE_URL` to
a host database reached through `host.docker.internal`, mapped with
`extra_hosts`. Point it at your own database if that does not apply.

Bundled cases in `backend/seed/` are loaded at startup and overwrite any stored
case with the same `case_id`. Cases created in the UI use their own ids and are
not touched.

## Run the backend locally

```bash
cd backend
pip install -r requirements.txt
DATABASE_URL=postgresql://graderh02:change_me@localhost:5432/graderh02 \
  uvicorn app.main:app --reload
```

The API is then on `http://localhost:8000`.

## Configuration

| Variable | Purpose |
|---|---|
| `APP_USERNAME` | TA account username |
| `APP_PASSWORD` | TA account password |
| `DATABASE_URL` | PostgreSQL connection string |

All routes except `GET /` and `POST /api/login` require a Bearer token from
`/api/login`. There is a single shared TA credential and no per-user accounts.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | health check |
| POST | `/api/login` | exchange credentials for a token |
| POST | `/api/logout` | revoke the current token |
| GET | `/api/cases` | list cases with a short summary |
| GET | `/api/cases/{id}` | read one full case |
| POST | `/api/cases` | create a case |
| PUT | `/api/cases/{id}` | replace a case |
| DELETE | `/api/cases/{id}` | delete a case |
| GET | `/api/master/device-types` | list device types |
| POST | `/api/master/device-types` | add a device type |
| PUT | `/api/master/device-types/{code}` | rename a device type |
| DELETE | `/api/master/device-types/{code}` | remove a device type |
| POST | `/api/parse-pkt` | decode a `.pkt` upload into `StudentJSON` |
| POST | `/api/solve` | return the expected addressing for `{case, npm}` |
| POST | `/api/grade` | grade a `.pkt` upload against a case |
| POST | `/api/grade-json` | grade a `StudentJSON` body, used by tests |

Example, run from the repository root against the local backend:

```bash
curl -F "case=@backend/tests/bgn_case.json;type=application/json" \
     -F "npm=2406123456" \
     -F "file=@/path/to/student.pkt" \
     http://localhost:8000/api/grade
```

## Authoring rules

- **NPM** must be exactly 10 digits, numbers only. The form and the API both
  enforce it, because a shorter value still resolves variables and would produce
  a wrong answer key without any error.
- **Count** is an expression over the case variables, for example
  `500 + ((NPM3 % 35) + 2)`. Every modulo is offset by two so a device count
  cannot reach zero.
- **Device name** is the exact name checked in the student's file. Each graded
  device is worth 5 points.
- **Not graded by IP** marks a device with no address on the subnet's plan: a
  device behind a home gateway, or a layer 2 access point. It still counts
  toward the subnet size and still appears in the expected addressing.
- **Subnet order** is chosen per upload for subnets that need the same mask:
  by host need (largest first) or by subnet code (Z to A). Larger blocks are
  always allocated first.
- **Recommended prefix** ends the results: the smallest single block that fits
  every address the VLSM plan allocates.

## Scoring

Each subnet earns up to 4 network points: DHCP pool, pool mask, pool gateway,
and a gateway held by a router. Each graded device earns up to 5 points: name,
DHCP configuration, IP range, subnet mask, and default gateway.

Devices marked `exclude_from_grading` earn no points and are left out of the
report, but they still size the subnet. The manual items (`note_name_npm`,
`palette_boxes`, `device_labels`, `wireless_dots`) are listed for the TA to
check by eye and are not auto-scored.

## Tests

```bash
cd backend
pip install pytest
python -m pytest -q
```

`test_solver.py` and `test_grader.py` have no external dependencies.
`test_decode.py` reads a `.pkt` from a fixed absolute path on the author's
machine, so it fails on a fresh clone until that path is updated.

## Decoder notes (ptdecoder fork)

The vendored `ptdecoder` is patched for Packet Tracer 8.2.2 files:

1. **Reference id and connections.** PT 8.x stores the reference id as a child
   `<SAVE_REF_ID>` element rather than a `DEVICE` attribute, so cables could not
   be resolved. It is now captured and connections resolve.
2. **Notes.** `<NOTE>` lives inside `PHYSICALWORKSPACE`, which was in the
   heavy-skip list. Removing it from the skip set captures identity and
   subnet-label notes while their heavy children stay skipped.
3. **Model.** The device `model` attribute is read from `ENGINE/TYPE`.
4. **Port matching.** Connection resolution falls back to a trailing port index
   (for example `FastEthernet0/1` to interface 1) when names do not match.

## Known limitations

- DHCP pools are read only from the router CLI `running-config`. Pools
  configured through the Packet Tracer GUI are not captured, so students must
  use `ip dhcp pool` in the CLI.
- Results are not stored, so there is no history or audit trail.
- There is a single shared TA account and no per-user permissions.
- Grading is limited to IPv4.
