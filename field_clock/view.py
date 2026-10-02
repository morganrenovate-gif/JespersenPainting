"""TIME-004 repository-only field clock development preview. No identity or provider adapter.

The caller supplies already-authorized *current* assignment display labels. Selection
is positional; no provider IDs or accounting data are rendered. Never use this preview
for actual work time: browser-local preview events are not authoritative records.
"""

from html import escape
from pathlib import Path


def render_field_clock(assignments: tuple[str, ...]) -> str:
    """Render the shell for the synthetic pending-event interaction in clock.js."""
    if type(assignments) is not tuple or any(
        type(label) is not str or not label.strip() or label != label.strip()
        for label in assignments
    ):
        raise ValueError("assignments must be a tuple of nonempty, trimmed display labels")
    if len(assignments) != len(set(assignments)):
        raise ValueError("ambiguous assignment labels")
    if len(assignments) == 1:
        choice = (f'<p class="job-name" id="selected-job">{escape(assignments[0], quote=True)}</p>'
                  '<p class="hint">Today’s assigned job</p>')
    elif assignments:
        items = ''.join(
            f'<label class="job-choice"><input type="radio" name="job" value="{index}">'
            f'<span>{escape(label, quote=True)}</span></label>'
            for index, label in enumerate(assignments)
        )
        choice = ('<fieldset id="job-choices"><legend>Choose today’s job</legend>'
                  f'{items}</fieldset>')
    else:
        choice = '<p class="empty">No current assignment is available. Ask your crew lead.</p>'
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        '<title>Field clock · Jespersen</title><link rel="stylesheet" href="clock.css">'
        '<script src="pending.js" defer></script><script src="clock.js" defer></script></head><body>'
        '<a class="skip" href="#main">Skip to field clock</a>'
        '<main id="main" class="clock" data-assignment-count="' + str(len(assignments)) + '">'
        '<header class="mast"><p class="eyebrow">Jespersen / Field time</p>'
        '<h1>Field clock</h1></header>'
        '<p class="preview">Development preview · Events stay in this browser until simulated replay. '
        'Not a work-time record. Do not use for work time.</p>'
        '<section class="work" aria-labelledby="work-heading">'
        '<p class="step">01 / Current work</p><h2 id="work-heading">Your assignment</h2>'
        f'<div id="choices">{choice}</div>'
        '</section><section class="shift" aria-labelledby="shift-heading">'
        '<p class="step">02 / Time on job</p><h2 id="shift-heading">Clocked out</h2>'
        '<p id="status" class="status" role="status" aria-live="polite">Ready to clock in</p>'
        '<div id="running" hidden><p class="running-label">Clock running · <strong id="active-job"></strong></p>'
        '<p class="timer" id="elapsed" role="timer" aria-label="Elapsed time">00:00:00</p>'
        '<p class="start">Clocked in at <time id="started"></time></p></div>'
        '<p id="finished" class="finished" hidden></p>'
        '<button id="action" class="action" type="button"' +
        (' disabled' if len(assignments) != 1 else '') + '>Clock In</button>'
        '</section><section class="sync" aria-labelledby="sync-heading">'
        '<p class="step">03 / Local event register</p><h2 id="sync-heading">Preview pending status</h2>'
        '<p id="sync-status" class="sync-status" role="status" aria-live="polite">Checking local preview events</p>'
        '<p id="latest-event" class="latest-event" hidden></p>'
        '<label class="connection"><input id="connection" type="checkbox"> Simulate connection available</label>'
        '<button id="retry" class="retry" type="button" disabled>Retry preview replay</button>'
        '</section><footer><p>Field time / job site · synthetic preview only</p></footer></main></body></html>'
    )


def stylesheet() -> str:
    return Path(__file__).with_name("clock.css").read_text(encoding="utf-8")
