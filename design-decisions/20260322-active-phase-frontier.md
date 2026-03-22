# ADR-002: active_phase is a Forward-Only Frontier

**Date**: 2026-03-22
**Status**: Accepted

## Context

`FlightSession.active_phase` stores the current checklist phase slug. The question
arose when designing the "Continue" flow: if the pilot navigates backward (Prev
button or sidebar) to review an earlier procedure, should `active_phase` follow
that movement?

## Decision

`active_phase` advances **forward only**. It represents the furthest procedure the
pilot has actively reached — the frontier — not the procedure currently on screen.

It moves forward in two cases only:
1. The pilot presses Next (explicit advancement, even with unchecked items)
2. All visible items in the current procedure are checked (auto-advance)

Backward navigation (Prev, sidebar click to an earlier step) does **not** change
`active_phase`.

"Continue" after returning to the profile page resumes at `active_phase`, not at
the literal last page visited.

## Options Considered

**Literal last-visited tracking**: `active_phase` follows every navigation event,
including backward. Rejected — if the pilot is about to taxi and navigates back to
CDU Preflight to re-check something, Continue should not send them back to CDU
Preflight.

## Consequences

- The sidebar "done" indicator for a procedure is determined by whether
  `procedure.step < active_phase_step` (position relative to frontier), not
  solely by whether all items are checked.
- A pilot can review and re-check items in earlier procedures without losing their
  place.
- `active_phase` must be updated in the view (or via a lightweight endpoint) when
  the pilot presses Next or when auto-advance fires.
- If a pilot navigates backward and re-checks items in a "done" procedure, those
  items are saved to `FlightItemState` normally — no special handling needed.
