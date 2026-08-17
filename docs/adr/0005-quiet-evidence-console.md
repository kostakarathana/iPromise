# ADR 0005: Quiet evidence console

Status: accepted on 2026-08-17

## Context

The first console proved the workflow but presented every fact as a card, badge,
icon, warning, or timeline event. At a 1280×720 viewport the evidence began below
the fold and the selected response did not appear until far later in the page.
That hierarchy made the implementation look like a generic dashboard instead of
serious operational software.

The console has one job in the demo: let a judge identify the exact promise, the
failed observation, and the selected response in seconds. Architecture and
execution details still need to be available, but they must not compete with the
result.

## Decision

iPromise uses a **quiet evidence console**:

- A light-neutral, flat work surface with a 1120px maximum content width.
- One primary action, `Run audit`, in the promise-title row.
- A single code-native Quotecheck mark identifies iPromise; ordinary interface
  states use text and small dots rather than decorative icon tiles.
- The concrete promise name and scoped verdict replace dashboard or marketing
  headings.
- The exact quote, failed observation, checks, and one selected response form the
  default information hierarchy. Finding and action share one 2:1 split band;
  evidence then receives the full content width.
- Failed evidence is ordered first. Color is reserved for semantic status and is
  always paired with text or an icon.
- PR, issue, and email are not peer cards. Only the selected route is prominent;
  unused routes live behind a disclosure.
- The event log, run ID, control ID, runtime, model provenance, and legal scope are
  preserved behind native disclosure controls.
- Local/synthetic provenance stays persistently visible in the app header as
  `Local · Synthetic data`, not as an urgent alert. External action is shown only
  when a run contains its receipt URL.
- No sidebar or fake navigation is added until multiple real destinations exist.
- At narrow widths the response follows the finding, evidence becomes stacked
  rows, and the page must not scroll horizontally at 390px.

The visual system uses Geist, an 8px spacing rhythm, 6–8px radii, plain borders,
no gradients or glass effects, and no page-content shadows.

## Evidence used

- [Linear: Behind the latest design refresh](https://linear.app/now/behind-the-latest-design-refresh)
  argues that supporting interface chrome should not compete for attention it has
  not earned.
- [GitHub Primer layout](https://primer.style/product/getting-started/foundations/layout/)
  recommends clean, calm, uncluttered focus areas and familiar responsive mental
  models.
- [Primer DataTable guidance](https://primer.style/product/components/data-table/guidelines/)
  recommends concise cells, few columns, intuitive row order, and designed narrow
  layouts.
- [Atlassian elevation](https://atlassian.design/foundations/elevation/)
  reserves raised surfaces for cases where elevation communicates interaction.
- [Vercel Geist badge guidance](https://vercel.com/geist/badge) treats badges as
  short static metadata and warns that multiple badges per row usually indicate a
  missing column or hierarchy.

## Acceptance gates

- At 1280×720 the exact promise, failed finding, selected response, and first
  failed check are visible without scrolling; the evidence table uses the full
  content width.
- At 390px `scrollWidth` equals `clientWidth`; no quote, identifier, or action is
  clipped.
- The default completed view contains one primary button and at most one
  prominent semantic status.
- Keyboard focus remains visible and status never relies on color alone.
- Empty, running, error, local-snapshot, connected-local, configured-cloud, and
  proven-cloud states remain truthful without prototype-oriented wording in the
  primary interface.

## Consequences

The full event trail takes one click to inspect, which is intentional progressive
disclosure. New features must fit the hierarchy or add a genuinely functional
destination; they must not reintroduce card grids, ornamental metrics, or peer
actions merely to fill space.
