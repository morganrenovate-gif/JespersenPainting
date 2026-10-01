# Jespersen Intelligence UI Standard

## Binding

This repository inherits **UI-STD-1.0**, the canonical Corlentra Premium UI Architecture Standard.

Canonical source:
- `hedy://corlentra/ui-standard-v1`
- Founder OS page: `page_003fde3e61157542f9ca52d5072f457a`
- Standard: `UI-STD-1.0`

Jespersen project binding:
- Product: **Jespersen Painting Intelligence**
- Dominant visual archetype: **INDUSTRIAL OPERATIONS**
- Secondary influence: **DIGITAL BLUEPRINT**
- Density: **COMPACT**
- Motion intensity: **LOW to MODERATE**
- Primary users: owner, management, office staff, and field personnel
- Critical information: job status, estimated versus actual cost, labor hours, materials, revenue, margin, time exceptions, missing records, financial reconciliation, and required actions
- Priority rule: exceptions, risks, conflicts, and required actions outrank decorative metrics
- Preserve Jespersen brand identity and existing business workflows
- Favor aligned numeric columns, tabular numerals for financial/time values, ledgers/tables when operationally appropriate, clear exception states, touch-friendly mobile behavior, and restrained motion

This file is the public-repository mirror of the resolved UI-STD-1.0 design contract for autonomous agents. It supplements and does not override governance, security, accessibility, tenant isolation, client-specific brand rules, or explicit project constraints.

If this file is missing, internally inconsistent, or references an unresolved future UI standard version, UI implementation must fail closed rather than invent a replacement.

## 1. Identity and intent

Corlentra products must not rely on one-off aesthetic prompts. Every UI task starts by establishing product, user, workflow, usage environment, information density, emotional tone, and implementation stack. The visual system must emerge from that context. UI-STD-1.0 is a profile-selection and quality framework, not one universal theme.

## 2. Visual design profiles

Select one dominant archetype and optionally one secondary influence.

- **DIGITAL BLUEPRINT** — technical, architectural, grid-driven; appropriate for construction intelligence, evidence, estimating, underwriting, financial/job-costing, and project controls.
- **TELEMETRY COMMAND** — dense live-system control plane; appropriate for command centers, runtime monitoring, approvals, infrastructure, and dispatch.
- **CINEMATIC TECHNICAL** — premium depth, restrained transparency, and ambient light; appropriate for demos, executive/product showcases, and selected analytics.
- **KINETIC NEO-MINIMALISM** — minimal structure with strong typography, interaction, and movement; appropriate for public sites, onboarding, and customer workflows.
- **INDUSTRIAL OPERATIONS** — legible, compact, durable, practical; appropriate for field operations, contractor workflows, job costing, and workforce.
- **BRAND-SPECIFIC** — client/customer identity takes precedence over generic Corlentra aesthetics for client sites and consumer brands.

For Jespersen Intelligence, the required default is **Industrial Operations + Digital Blueprint**.

## 3. Color system

Define semantic tokens for Primary, Secondary, Accent, Background, Elevated Surface, Primary Text, Secondary Text, Border, Success, Warning, Critical, and Informational.

Avoid default Tailwind blue/purple and generic gradients unless the product brand specifically requires them. Ambient glow is allowed only when the selected profile supports it and must not reduce legibility.

## 4. Geometry and structure

Explicitly define radius, border weight, depth, grid, row height, and spacing.

Avoid the disconnected rounded-card dashboard as a default. Technical tools should favor precise boundaries, contiguous data, grids, ledgers, timelines, and matrices. Structure must reflect the domain and workflow.

## 5. Typography

Preferred families include Geist, Inter, SF Pro, and IBM Plex Sans when available and appropriate.

Use mono/tabular treatment for IDs, timestamps, financial values, percentages, quantities, runtime states, hashes, and technical metadata. Do not use monospace everywhere. Typography must create hierarchy before decorative containers do.

## 6. Motion

Use motion only where it explains hierarchy, state, expansion, feedback, progress, or causality.

Baseline spring reference when applicable:
- mass: 0.8
- damping: 15
- stiffness: 100

Tune by interaction. Every surface declares motion intensity NONE, LOW, MODERATE, or HIGH. Jespersen operational surfaces are LOW/MODERATE. Respect reduced-motion. Avoid generic linear fades and gratuitous motion.

## 7. Live and telemetry visualization

Animate telemetry only where a real process or state exists. Never fake telemetry.

Valid patterns include scanning indicators, controlled pulses, processing lines, runtime activity, signal sweeps, progress traces, status ripples, live counters, and streaming events when those visuals map to real states such as RUNNING, PROCESSING, SYNCING, WAITING, FAILED, APPROVAL REQUIRED, CONNECTED, and DISCONNECTED.

## 8. Hover, focus, and interaction

Interaction feedback may use border illumination, accent transitions, text emphasis, subtle elevation, cursor-aware highlighting, surface tint, contextual controls, and focus rails.

Avoid gratuitous scaling, layout shift, and effects that obscure selection or status. No critical action may depend on hover alone.

## 9. Iconography

Use a coherent icon system such as Lucide with approximately 1.5px stroke where appropriate.

Do not box every icon inside rounded glass tiles. Icon treatment must follow the selected archetype and information hierarchy rather than becoming a decorative repeated motif.

## 10. Data-dense UI

Compact is acceptable when it remains readable.

- Align numeric columns.
- Keep row behavior predictable.
- Use persistent headers where useful.
- Group related data.
- Make exception states obvious.
- Right-align financial values with tabular numerals.
- Exceptions, risks, conflicts, and required actions outrank decorative metrics.
- Tables are first-class interfaces when the workflow calls for them.

## 11. Anti-generic rule

Mandatory review question:

> Could this interface have come from a generic “modern SaaS dashboard” prompt with only the logo changed?

If yes, redesign it.

Warning patterns include:
- giant heading plus four KPI cards
- unrelated rounded gray cards
- random Lucide icons
- purple CTA defaults
- excessive whitespace
- generic sidebar/chart/pills/glass combinations
- ornamental gradients

The product domain should be recognizable without its logo.

## 12. Responsive and mobile

Mobile is not compressed desktop.

For each major surface explicitly define what remains visible, collapses, scrolls, becomes drill-down, moves into a drawer, or changes interaction model.

Critical actions must be touch-friendly and reachable. Respect device safe areas and visual viewport behavior. Avoid desktop-width tables for information that must be acted on from a phone.

## 13. Accessibility

Meet appropriate contrast, keyboard navigation, visible focus, touch-target, semantic HTML, screen-reader, and reduced-motion requirements.

Status cannot be communicated by color alone. Accessibility is part of acceptance, not an optional polish pass.

## 14. Implementation quality

Use modular code, reusable primitives, semantic design tokens, centralized motion configuration, consistent layout systems, variant-based components, and explicit responsive states.

Avoid monolithic components, arbitrary one-off utility values, duplicated patterns, and unnecessary hardcoding. Extend the existing product design system instead of replacing it without evidence.

## 15. Design review gate

Before accepting UI work, explicitly review:
- Product Fit
- Hierarchy
- Density
- Identity
- Motion
- Structure
- Data Presentation
- Responsiveness
- Accessibility
- Anti-Generic quality

Generic AI SaaS output is unfinished. Review against the actual workflow and user role, not screenshot aesthetics alone.

## 16. Required design assignment

Every UI implementation brief must declare:
- Product
- Surface
- Dominant Visual Archetype
- Secondary Influence, if any
- Palette
- Density
- Motion Intensity
- Primary Users
- Critical Information

Final instruction: **Do not merely assemble components. Design the system.**

## 17. Current product mapping

Jespersen Intelligence defaults to **Industrial Operations + Digital Blueprint** unless a more specific Jespersen project guide narrows the surface.

## 18. Precedence and exceptions

UI-STD-1.0 supplements but does not override the Master Agent Constitution, Core Operations Contract, security/accessibility requirements, client-specific brand systems, or explicit project guides.

Project guides may narrow or specialize the selected profile; they must not silently weaken governance, accessibility, tenant isolation, or product-specific constraints.

Future changes to this standard must be versioned.
