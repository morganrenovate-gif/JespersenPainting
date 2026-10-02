# TIME-004 · field clock pending-event development preview

**Design assignment:** Product: Jespersen Painting Intelligence. Surface: field employee mobile clock and pending-time status. Dominant visual archetype: Industrial Operations. Secondary influence: Digital Blueprint. Palette: existing Jespersen semantic ink/green, warm neutral and informational/warning/critical tokens. Density: compact and touch-first. Motion intensity: LOW (timer numbers only). Primary users: field painters and crew members using a phone at a job site. Critical information: selected synthetic job, captured event/time, pending/sync state and next available action.

`render_field_clock(tuple_of_current_job_labels)` returns a standalone HTML shell; serve `clock.css`, `pending.js` and `clock.js` beside it in a **dev-only preview**. Supply invented assignments only for this slice. Browser-local events are **not authorized work-time records**; the prominent warning remains visible. There is no auth, location, live receiver, network call, service worker, production sync, or provider integration. This is not a deployed or accepted field-time solution.

Synthetic example:

```python
from field_clock.view import render_field_clock
html = render_field_clock(("Synthetic Bridge Repaint",))
# Serve html and its three sibling assets in a development preview only.
```

## Local queue / replay boundary

`pending.js` exports `createQueue(storage, receiver, makeId)` and `memoryReceiver()` for synthetic fixtures. Storage implements `getItem(key)` and `setItem(key, serialized)` (the preview uses `localStorage`); `makeId()` provides a unique stable ID (the browser uses `crypto.randomUUID()`). A captured `{id, kind: 'in'|'out', job, at: ISO timestamp, startId}` is written before the UI changes. The single versioned JSON document stores up to 100 pending events and the active preview shift. A reload recovers pending events and a running timer from the saved start; clock-out links to the start ID. Invalid/unreadable storage disables capture without deleting anything. Full/blocked storage fails closed. Do not clear browser storage while relying on the preview: browser storage can be evicted, deleted or shared across tabs, and is not durable time truth.

`receiver.accept(event)` must acknowledge or throw and **dedupe by ID**, rejecting conflicting payloads with the same ID. `queue.replay()` attempts pending events in order, saves each acknowledgement locally, and stops at the first failure. An acknowledgement-write failure leaves the same event pending: the receiver must dedupe the next attempt. `memoryReceiver()` is an in-memory demonstration only, scoped to the current tab; a reload creates a new demonstration receiver. The checkbox simulates connectivity; it does not read real connection status. Replay runs only on explicit Retry preview replay, never in the background. A success means *accepted by that tab’s synthetic fixture*, not transmitted or verified. The visible local pending count and clock state survive a reload if browser storage remains available. Pending, replay-complete and error copy are text announcements as well as border/token variations.

## UI-STD-1.0 repository review

- **Product fit / hierarchy:** assignment then clock action, with contiguous local-event register and visible warning; pending/failure state and retry precede decorative content. This does not imply production time capture.
- **Density / identity / structure:** numbered, bounded work/time/register sections, industrial green/ink and warm neutral palette; blueprint step index and tabular time/count, not SaaS metric cards.
- **Motion / data:** running timer ticks once per second; no fake telemetry or sync animation. Reduced motion removes animations/transitions.
- **Responsiveness:** phone-first single column; nothing critical collapses or scrolls horizontally. Full-width 64px clock action, 52px choices, checkbox row and retry button; safe-area padding.
- **Accessibility:** semantic sections/headings, native inputs/buttons, live text states (not timer ticks), visible focus, skip link and status text independent of color. Browser and assistive-technology verification is still needed by independent QA.
- **Anti-generic:** a job-site assignment/time register, not a dashboard. No office/accounting internals appear.

`tests/test_field_clock_view.py` checks markup, escaping and UI structure. `tests/field_clock_interaction.cjs` checks synthetic recovery, replay failure/retry, duplicate acknowledgement, write-failure ambiguity and existing clock flows with a deterministic clock; Python invokes it when Node is available. Trusted workflow executes tests after this implementation lane; no test pass or staging acceptance is claimed here. Rollback: revert TIME-004 changes in `field_clock/` and the two field-clock test files; no external state is changed.
