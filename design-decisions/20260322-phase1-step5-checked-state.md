# ADR-001: Phase 1 Step 5 — Server-Side Checked State in procedure_detail

**Date**: 2026-03-22
**Status**: Accepted
**Deciders**: h (project owner)

## Context

The checklist was entirely frontend-stateful: clicking a row toggled a CSS class
in JS with no persistence. Steps 3 and 4 added the `FlightItemState` model and
`/api/check` / `/api/uncheck` endpoints. Step 5 wires the frontend to those
endpoints and makes the view annotate items with their persisted state so the
page renders correctly on reload.

## Decision

**View annotation**: Compute a `checked_css` string (`'ci-manual'`, `'ci-auto'`,
or `''`) per item in `procedure_detail`, using a single bulk query of
`FlightItemState` filtered to the visible item IDs. String is set directly on the
model instance (same pattern as the existing `.lowlight` annotation). Template
applies it as an additional CSS class and conditionally renders the tick SVG.

**JS wiring**: Replace the pure-client-side `toggleItem` with an optimistic-update
version that fires `fetch` to `/api/check/` or `/api/uncheck/` after applying the
visual change, and rolls back the CSS/counters on `.catch()`.

**Counter init**: `checkedCount`, `autoCount`, `manualCount` initialised from
`document.querySelectorAll` on page load rather than hardcoded to 0, so the
progress ring is correct on first paint.

## Options Considered

**View — expose full FlightItemState object to template**: Rejected. More template
logic, and the template has no need for `status`/`source` independently; only the
combined CSS class string is needed.

**View — template tag querying DB per item**: Rejected. N+1 query pattern;
inconsistent with how other view-layer decisions are made in this codebase.

**JS — fire-and-forget (no rollback)**: Rejected. Silent divergence between UI and
DB if the flight session has expired mid-use is worse than a visible rollback.

**JS — pessimistic update (wait for API response)**: Viable, but optimistic feels
more natural for a tap-to-check interaction and the API is always local.

## Consequences

- Page reload now correctly reflects all manual/auto checks made during the flight.
- `skipped` and `pending` status values (Phase 2) render as unchecked — this is
  intentional and correct for Phase 1. When Phase 2 adds visual states for these,
  the view `elif` chain extends trivially.
- Non-2xx HTTP errors from the API (e.g. 403 session expired) are silently rolled
  back in Phase 1. Phase 2 session expiry handling should add a redirect.
- `ci-auto` rows cannot be manually unchecked via click. This is intentional —
  auto state is cleared only by session reset or plugin command (Phase 2).

## Assumptions at Time of Decision

- `FlightItemState` rows with `status != 'checked'` are absent in Phase 1 (no
  auto-check engine yet). Design handles them gracefully (renders as unchecked).
- The flight session does not expire mid-flight under normal Phase 1 usage
  (single-user, local dev + production with active session).
