# AGENTS.md

Project: graderH02 - a web app that grades Cisco Packet Tracer IP-addressing
labs (TA authors a case; student uploads a `.pkt`; system decodes, solves VLSM,
and grades).

## Stack

React (Vite + TypeScript) frontend, FastAPI backend, Postgres. Deployed via
docker compose at `grader-h02.teyyow.web.id`. Auth: `admin` / `admin`.

## antislop

UI, copy, and frontend work must follow the globally-enabled antislop agent
(opencode skill `antislop`, with `antislop-ui`). It is installed in the global
opencode config, not this repo.

- Mode: After (audit, list findings, get approval, fix) for existing screens;
  During for new screens.
- Direction: `DESIGN.md` (Design Read + dials live there).
- Dials: ENERGY Low, RHYTHM Sequence, MOTION Low.

Hard Gate (em dash, gradients, glass > 1, shadow outside modal, looping motion,
fake copy, AA contrast, Escape-closable modals, 360px no-overflow) is absolute.
