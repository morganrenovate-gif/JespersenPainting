# ECON-003 · read-only owner job-economics view

**Design assignment:** Product: Jespersen Painting Intelligence. Surface: owner job-economics view. Dominant archetype: Industrial Operations. Secondary influence: Digital Blueprint. Palette: graphite/ink on warm neutral with defined informational, warning, critical and success tokens. Density: compact. Motion: LOW (no ambient animation). Users: owner, management and office staff. Critical information: source-separated financial/time evidence, traceable comparisons, conflicts, missing/stale records and required review actions.

`render_job_economics(job, links=())` in `job_economics.view` takes an existing `JobEconomics` snapshot and optional *caller-approved* `ComparisonLink` tuple, returning escaped standalone HTML. Serve `job_economics/view.css` beside the HTML as `view.css` (or use `stylesheet()` for a host that bundles assets). The caller remains responsible for authorized job scope, snapshot retrieval, establishing link comparability and serving the page behind the existing private operational access controls. **No route, authentication, provider fetch, job mapping, runtime integration or deploy is added here.** Do not publish real job output in the public repository. The view never treats matching values as verified, retained values as fresh, missing as zero, or source-specific workbook calculations as job-wide truth. Workbook source assertions appear within the historical workbook slot with sheet/cell provenance; workbook row detail, recomputations and discrepancies require separate source review. The snapshot cannot establish what the job made or lost; there is no supported cross-source margin calculation in this model.

Synthetic-only usage (invented test fixture, **not** client data):

```python
from job_economics.view import render_job_economics
from test_job_economics_model import invented_job  # test fixture only

html = render_job_economics(invented_job())
# Serve html and view.css together in an authorized development host.
```

## UI-STD-1.0 review · repository implementation (not browser/staging validation)

- **Product Fit:** owner-first assessment and review queue precede the eight evidence slots; no field-worker accounting view.
- **Hierarchy:** conflicts and coverage exceptions precede links and source ledger; withheld conclusion is explicit.
- **Density:** contiguous ledger rows, compact type and aligned tabular values; no KPI-card grid.
- **Identity:** numbered job-source ledger, precise boundaries and construction-operations palette with blueprint-like reference links, not interchangeable SaaS chrome.
- **Motion:** none except native anchor navigation; reduced-motion disables smooth scrolling.
- **Structure:** semantic sections, tables with row/column headings and anchored fact references.
- **Data Presentation:** literals are escaped and shown without assumed units/currency; fact and coverage states use text; comparison links expose both source IDs, record IDs, fact IDs, locators and literal values; unresolved comparability remains explicit.
- **Responsiveness:** at 700px the ledger becomes stacked labeled rows, comparison links become single-column 44px targets; no phone-width data-table scroll needed. Safe-area padding is applied.
- **Accessibility:** skip link, visible focus, semantic headings/table labels and non-color status. Browser/assistive-tech contrast and keyboard inspection remain for independent QA.
- **Anti-Generic:** an evidence ledger and reviewer actions, rather than decorative margin cards, anchor the surface in painting operations.

`tests/test_job_economics_view.py` uses invented synthetic records only to check source separation, links, coverage, HTML escaping and structural mobile/accessibility CSS contracts. A trusted workflow runs executable tests after implementation; this document does not claim they passed. Live staging acceptance and real reconciliation remain separate. Rollback: revert the view module, stylesheet, synthetic tests and this document; no migration or external state.
