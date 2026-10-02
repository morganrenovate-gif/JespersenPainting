# TIME-005 · synthetic field clock adversarial preview

**Design assignment:** Product: Jespersen Painting Intelligence. Surface: field employee mobile clock and local development-preview time status. Dominant visual archetype: Industrial Operations. Secondary influence: Digital Blueprint. Palette: existing Jespersen semantic ink/green, warm neutral and informational/warning/critical tokens. Density: compact and touch-first. Motion intensity: LOW (timer numbers only). Primary users: field painters and crew members using a phone at a job site. Critical information: selected synthetic job, captured event/time, active or corrected shift state, pending/replay state, exceptions and next available action.

`render_field_clock(tuple_of_current_job_labels)` returns a standalone HTML shell; serve `clock.css`, `pending.js` and `clock.js` beside it in a **dev-only preview**. Supply invented assignments only. Browser-local events are **not authorized work-time records**; the warning remains visible. There is no auth, live location source, network call, production sync or provider integration. This is not deployed/accepted field time.

Synthetic example:

```python
from field_clock.view import render_field_clock
html = render_field_clock(("Synthetic Bridge Repaint",))
```

## Local queue / replay boundary

`pending.js` exports `createQueue(storage, receiver, makeId)` and `memoryReceiver()` for synthetic fixtures. Storage implements `getItem(key)` and `setItem(key, serialized)`; browser preview uses `localStorage`. A captured event is written before UI changes. The versioned JSON document stores up to 100 pending events, an active start and a local history, including review requests; legacy preview state without history is read without deleting its pending or active data. A replay acknowledgement removes only the pending copy, not history. Invalid/unreadable storage disables capture without erasing anything. Full/blocked storage fails closed. Browser storage can be evicted, deleted or shared across tabs and is not durable time truth.

`queue.capture('in'|'out', job, date, location)` rejects duplicate starts and early/mismatched ends. Location may be `ok`, `unavailable` or `suspicious`; the latter two are review signals, not hard blocks. The preview defaults to unavailable when there is no synthetic location callback. `queue.switchJob(job, date, location)` atomically appends a closing event and a new start at the same instant, with no overlapping interval. The UI does not offer switching yet; use the synthetic queue interface for adversarial coverage. `needsClockOutReview(date)` flags a still-active start after 16 hours; `requestReview('forgotten-out'|'correction', referenceId, note, date)` appends a linked request, never rewrites or auto-closes a shift. Review requests in the UI refer to the active start for forgotten-out, or the latest captured clock event for correction. No approval or authoritative correction workflow exists in this preview.

`receiver.accept(event)` must acknowledge with `{id: event.id, duplicate: boolean}` or throw, deduping by ID and rejecting conflicting payloads. Replay saves each acknowledgement locally, stops at first failure and keeps the same ID on ambiguous acknowledgement-write failures. `memoryReceiver()` is in-memory only, scoped to the tab; a reload creates a new demonstration receiver. The checkbox simulates connectivity, not real network status. Replay is explicit only. A success means accepted by that tab’s synthetic fixture, not transmitted or verified.

## UI-STD-1.0 repository review

- **Product fit / hierarchy:** assignment then clock action, contiguous time and event register, with explicit pending, exception and review actions; warning stays visible.
- **Density / identity / structure:** numbered, bounded job-site sections in ink/green and warm neutral; blueprint step index and tabular time, no SaaS metric cards.
- **Motion / data:** running timer ticks once per second; no fake telemetry or sync animation. Reduced motion removes transitions.
- **Responsiveness:** phone-first single column; nothing critical collapses or scrolls horizontally. Full-width 64px clock action and 52px review/retry buttons; safe-area padding.
- **Accessibility:** native inputs/buttons and labeled note, semantic sections/headings, live text states (not timer ticks), visible focus, skip link and exception copy independent of color. Independent browser/assistive-technology verification remains outstanding.
- **Anti-generic:** assignment/time register and reviewable site exceptions, not an office dashboard or accounting interface.

`tests/field_clock_adversarial.cjs` and `tests/field_clock_interaction.cjs` contain deterministic synthetic-only cases. Python wrappers invoke them when Node is available. Trusted workflow runs executable tests after implementation; no test pass, live-provider or staging acceptance is claimed here. Rollback: revert TIME-005-specific field-clock changes and tests; no external state changes.
