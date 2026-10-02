# TIME-003 · field clock repository slice

**Design assignment:** Product: Jespersen Painting Intelligence. Surface: field employee mobile clock. Dominant archetype: Industrial Operations. Secondary influence: Digital Blueprint. Palette: existing Jespersen semantic ink/green, warm neutral, informational/warning/critical tokens. Density: compact and touch-first. Motion intensity: LOW (none beyond ticking numbers). Primary users: field painters and crew members on a phone at a job site. Critical information: current job or job choices, clocked-in/out state, elapsed time, start time and next action.

`render_field_clock(tuple_of_current_job_labels)` returns a standalone HTML shell; serve `clock.css` and `clock.js` beside it. The host must supply already-authorized, unambiguous current assignment labels. It must not pass provider records, IDs or office data to this surface. This repository has **no field-time event contract, persistence adapter, route, authentication layer, or provider sync**. Consequently the controls here are explicitly a **development preview**: clicking Clock In/Out changes only the current page, and a reload loses the state. Never present this UI as a working time recorder or use it for work time. Wiring actual capture and authorization requires a separately governed runtime boundary; TIME-004 owns pending/offline sync. No QuickBooks/Hedy behavior is asserted.

Synthetic example (invented names only):

```python
from field_clock.view import render_field_clock
html = render_field_clock(("Synthetic Bridge Repaint",))
# Serve html with clock.css and clock.js in an authorized dev preview only.
```

## UI-STD-1.0 repository review

- **Product fit / hierarchy:** job choice or assigned job precedes time action; on start, the running state, job, elapsed time, start time and Clock Out become the focus. Development-preview warning stays visible.
- **Density / identity / structure:** numbered contiguous work/time sections with precise boundaries, construction-operations palette and a blueprint-like step index; no cards, gradient or generic dashboard chrome.
- **Motion / data:** timer changes once per second only in the running state; tabular digits and plain-language states, no color-only signal or simulated sync telemetry. Reduced motion removes animation/transition.
- **Responsiveness:** single-column phone-first layout; no collapsed critical controls or horizontal table scrolling. Full-width 64px action and 52px choices, viewport-safe-area padding.
- **Accessibility:** semantic headings, fieldset/legend and native radio/button, live state announcement (not every timer tick), timer label, visible focus, skip link, text state, reduced-motion CSS. Browser/assistive technology review remains for independent QA.
- **Anti-generic:** a job-site assignment/time register rather than KPI cards or generic sidebar. Office/accounting information is absent.

`tests/test_field_clock_view.py` checks rendering, ambiguity, escaping and structural CSS; `tests/field_clock_interaction.cjs` checks synthetic transitions with a deterministic clock, invoked by the Python test when Node is available. Trusted checks run after this implementation lane; no test or staging acceptance is claimed here. Rollback: revert this directory and its two test files. No external state is altered.
