"""ECON-003: read-only, source-separated owner HTML for ECON-001/002 snapshots.

Accepts caller-supplied evidence and explicit comparison links only. No retrieval,
identity matching, aggregation, or accounting source-of-truth promotion occurs.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from job_economics.model import (
    CATEGORIES, ComparisonLink, EvidenceFact, FactRef, JobEconomics, find_evidence,
)

LABELS = {
    "estimate": "Estimate", "change_orders": "Change orders", "time": "Time",
    "labor": "Labor cost", "materials": "Materials", "invoices": "Vendor invoices",
    "quickbooks": "QuickBooks", "historical_workbooks": "Historical workbooks",
}
STATES = {
    "available": "Available", "missing": "Missing", "needs_review": "Needs review",
    "stale": "Stale", "error": "Error",
}
FACT_STATES = {
    "missing": "Missing", "unknown": "Unknown", "malformed": "Malformed",
    "unsupported": "Unsupported",
}


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _reference(ref: FactRef) -> str:
    return f"{LABELS[ref.category]} / {ref.source_id} / {ref.record_id} / {ref.fact_id}"


def _comparison(a: EvidenceFact, b: EvidenceFact, field: str) -> str:
    if a.field != field or b.field != field or a.state != "present" or b.state != "present":
        return "Not comparable — field or value unavailable"
    if type(a.value) is not type(b.value):
        return "Not comparable — value types differ"
    return "Conflict — source values differ" if a.value != b.value else "Agree — linked source values match"


def _row(anchor: str, field: str, fact_id: str, source_id: str, record_id: str,
         locator: str | None, value: object | None, fact_state: str, source_state: str,
         *, workbook: bool = False) -> str:
    state = ("Source-reported" if source_state == "available" else
             f"Retained · {STATES[source_state].lower()}") if fact_state == "present" else FACT_STATES[fact_state]
    label = "Workbook source-reported" if workbook and fact_state == "present" and source_state == "available" else state
    return (
        f'<tr id="{anchor}"><th scope="row">{_text(field)}<small>Fact {_text(fact_id)}</small></th>'
        f'<td data-label="Source / record">{_text(source_id)}<small>{_text(record_id)}</small></td>'
        f'<td data-label="Locator">{_text(locator) if locator is not None else "Not supplied"}</td>'
        f'<td data-label="Reported value" class="value">{_text(value) if fact_state == "present" else "Not reported"}</td>'
        f'<td data-label="Evidence state"><span class="state" data-state="{_text(source_state)}">'
        f'{_text(label)}</span></td></tr>'
    )


def render_job_economics(job: JobEconomics, links: tuple[ComparisonLink, ...] = ()) -> str:
    """Return escaped standalone HTML. Comparison links assert caller-reviewed comparability.

    Workbook source facts stay inside the workbook section. Its recomputation and
    discrepancies are not promoted to cross-source comparisons or job margin.
    """
    findings = find_evidence(job, links)  # validates source envelope and dangling refs
    facts: dict[FactRef, tuple[EvidenceFact, str, str]] = {}
    sections = []
    for index, category in enumerate(CATEGORIES):
        source = getattr(job, category)
        rows = []
        for record_index, record in enumerate(source.records):
            for fact_index, fact in enumerate(record.facts):
                ref = FactRef(category, record.source_id, record.record_id, fact.id)
                anchor = f"fact-{index}-{record_index}-{fact_index}"
                facts[ref] = (fact, anchor, source.state)
                rows.append(_row(anchor, fact.field, fact.id, record.source_id, record.record_id,
                                 fact.locator, fact.value, fact.state, source.state))
            if record.workbook is not None:
                # Show the workbook's *own* job-level source assertions and cell locators.
                # Rows and recomputed metrics stay in the governed workbook detail;
                # no workbook figure becomes a normalized ECON fact or accounting value.
                book = record.workbook
                for fact_index, fact in enumerate(book.job.facts):
                    provenance = fact.provenance
                    locator = (f"{provenance.sheet_name}!{provenance.cell}"
                               if provenance is not None else None)
                    rows.append(_row(f"workbook-{index}-{record_index}-{fact_index}", fact.field,
                                     fact.id, record.source_id, book.job.id, locator,
                                     fact.value, fact.state, source.state, workbook=True))
        body = "".join(rows) or '<p class="empty">No source records supplied. Not zero.</p>'
        if rows:
            body = ('<div class="ledger"><table><thead><tr><th scope="col">Field</th>'
                    '<th scope="col">Source / record</th><th scope="col">Locator</th>'
                    '<th scope="col" class="value">Reported value</th><th scope="col">Evidence state</th>'
                    '</tr></thead><tbody>' + body + '</tbody></table></div>')
        note = ('<p class="source-note">Workbook source assertions only. Workbook row detail, '
                'recomputed metrics and discrepancies require separate source review; not job-wide totals.</p>'
                if category == "historical_workbooks" and source.records else '')
        sections.append(
            f'<section class="source" aria-labelledby="source-{index}"><header class="source-head">'
            f'<h3 id="source-{index}"><span class="index">{index + 1:02d}</span> {_text(LABELS[category])}</h3>'
            f'<span class="state" data-state="{_text(source.state)}">{_text(STATES[source.state])}</span>'
            f'</header>{note}{body}</section>'
        )

    # Display all caller-linked comparisons, not just conflicts; agreement does
    # not verify that either source or the set of sources is complete.
    unique = sorted({(min(link.left, link.right), max(link.left, link.right), link.comparable_field)
                     for link in links})
    comparisons = []
    for left, right, field in unique:
        a, a_id, a_state = facts[left]
        b, b_id, b_state = facts[right]
        result = _comparison(a, b, field)
        if a_state != "available" or b_state != "available":
            result += " · retained source; freshness unresolved"
        comparisons.append(
            f'<li class="comparison"><strong>{_text(result)}</strong>'
            f'<span class="field">Compared field: {_text(field)} · caller-linked evidence</span>'
            '<div class="pair">'
            f'<a href="#{a_id}">{_text(_reference(left))} — {_text(a.value) if a.state == "present" else _text(a.state)}'
            f' ({_text(a.locator) if a.locator else "no locator"})</a>'
            f'<a href="#{b_id}">{_text(_reference(right))} — {_text(b.value) if b.state == "present" else _text(b.state)}'
            f' ({_text(b.locator) if b.locator else "no locator"})</a></div></li>'
        )
    coverage = [
        f'<li><a href="#source-{CATEGORIES.index(item.category)}"><strong>{_text(STATES[item.state])}'
        f' · {_text(LABELS[item.category])}</strong></a> — '
        + (f'{len(item.retained_facts)} retained fact(s); inspect below. Not current evidence.'
           if item.retained_facts else 'No facts supplied. Not zero.') + '</li>'
        for item in findings.coverage
    ]
    headline = ("In conflict — job result unresolved" if findings.conflicts else
                "Unresolved — job result not established")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>Job economics · {_text(job.job_id)} · Jespersen</title>'
        '<link rel="stylesheet" href="view.css"></head><body>'
        '<a class="skip" href="#main">Skip to job evidence</a><main id="main">'
        '<header class="mast"><p class="eyebrow">Jespersen / Painting Intelligence · Job economics</p>'
        f'<h1>Job {_text(job.job_id)}</h1><p class="synthetic-note">Read-only evidence snapshot. '
        'Not a live accounting statement.</p></header>'
        '<section class="assessment" aria-labelledby="assessment-title">'
        f'<p class="eyebrow">01 / Owner assessment</p><h2 id="assessment-title">{headline}</h2>'
        f'<p>{len(findings.conflicts)} explicit conflict(s); {len(findings.coverage)} source coverage exception(s). '
        'Reported amounts and hours below belong to their sources. What this job made or lost '
        'cannot be concluded from these records: no supported job-wide revenue, cost, or margin '
        'calculation is provided here. Matching values do not prove completeness.</p></section>'
        '<section class="review" aria-labelledby="review-title"><h2 id="review-title">Review before deciding</h2>'
        '<p>Resolve source disagreements and missing, stale, review or error evidence with the office. '
        'Do not treat retained values as current.</p>'
        f'<ul>{"".join(coverage) if coverage else "<li>No coverage exceptions reported; completeness is not verified.</li>"}</ul>'
        '</section><section class="comparisons" aria-labelledby="comparisons-title">'
        '<h2 id="comparisons-title">Linked comparisons</h2><p>Only caller-linked source facts are compared. '
        'Open either reference to inspect its source, record and locator; no automatic matching.</p>'
        f'<ol>{"".join(comparisons) if comparisons else "<li>No explicit comparisons supplied. No agreement or conflict inferred.</li>"}</ol>'
        '</section><section class="sources" aria-labelledby="sources-title">'
        '<h2 id="sources-title">Source evidence ledger</h2><p>Values are literal source reports, '
        'not combined totals. Missing facts are not zero. Units and comparability require source review.</p>'
        f'{"".join(sections)}</section></main></body></html>'
    )


def stylesheet() -> str:
    """Expose the companion stylesheet for hosts that serve the standalone view."""
    return Path(__file__).with_name("view.css").read_text(encoding="utf-8")
