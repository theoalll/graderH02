# DESIGN.md - IP Addressing Grader

> Design Read: this is a focused internal TA tool for grading Cisco Packet Tracer
> labs. The look is calm and technical on purpose - no sales gloss, no decoration.
> Every surface exists to make one grading decision faster and less error-prone.

Design decisions for the grader frontend, recorded so the look is a choice and
not a model default.

## Product

An internal teaching-assistant tool for grading Cisco Packet Tracer
IP-addressing labs (VLSM/FLSM allocation, DHCP, gateway correctness). The
users are TAs; the content is technical network data. This drives every choice
below.

## Theme: dark, by deliberate choice (R-21)

Dark is justified here: it is a developer/technical tool used for long grading
sessions on config-heavy screens, where light surfaces cause glare and reduce
contrast for monospaced IP/config text. No toggle is shipped; the single fixed
theme is the product decision.

## Palette (R-01, R-29)

One blue-grey neutral ramp plus a single accent. Status colors are reserved for
real grading state, never decoration.

- Surfaces: `#0b0f17` bg → `#131925` → `#1a2233` → `#212b40` (single cool hue).
- Lines: `#242e40` / `#33405a`.
- Text: `#e7ecf5` / muted `#9aa7bd` / faint `#6b7891`.
- Accent (blue `#3aa0f2`): used only at the key moments — primary actions,
  focus ring, the brand mark, and the score readout. Deliberately *not* spread
  across links, chips, lines, and glows.
- Status: green `#36d399` (pass), amber `#f5b945` (partial), red `#f87171`
  (fail). These appear solely on grading results (real state).

## Typography (R-06)

`system-ui` for UI text; `ui-monospace` for IP addresses, masks, and gateway
values. Monospace is a readability decision for technical data, not an aesthetic
default, and is scoped to data cells only.

## Hierarchy tools (R-10, R-11, R-12, R-13)

- Radius: a 3-step scale (6 / 9 / 14px). Buttons and inputs are 9px, cards 14px
  — never pill-shaped across the board.
- Glass: exactly one surface (the sticky top bar) uses `backdrop-filter`.
- Shadow: only the modal elevates.
- Glow: none.
- Motion: hover/transition only (no loops) — the progress bar and card hover
  are the only movement.

## Layout

App, not landing page. Each screen is built around the one decision the TA
makes there: pick a case (Cases), configure a case (Builder), or grade an upload
(Submit → report). No stat row, no chart, no filler feed.

## Dials (Block 3)

Set explicitly so the look is intentional, not drift.

- ENERGY: Low. Calm, dense, workmanlike. No bursts, no hype, no celebratory
  motion. The only "energy" is the status color on a grading result, which is
  real signal, not decoration.
- RHYTHM: Sequence. The product is a strict step flow - Cases → Builder →
  Submit → Report. Screens stack in order; nothing runs in parallel or competes
  for attention.
- MOTION: Low. Hover/transition only (border, color, the thin progress bar). No
  loops, no entrance animation, no autoplay.
