# 1. Verify GitHub Pages deployment in publish CI

Date: 2026-07-04

## Status

Accepted.

## Context

The `publish-calendar` workflow fetches Airbnb bookings, rebuilds
`docs/index.html`, and commits to `main`. GitHub Pages then rebuilds
the live site from `main`/`docs` and serves it at
<https://dusteffect.github.io/airbnb/>.

Publishing is only complete when the live site actually serves the new
HTML (see [`CONTEXT.md`](../../CONTEXT.md) — **Publish**). But the
workflow used to end at `git push`, treating publish as complete once
the commit landed.

On 2026-07-02 a Pages build failed silently (`"Page build failed."`,
no diagnostic detail from GitHub). The workflow kept running on
schedule and kept succeeding — but because the *content* had not
changed since the failure, the "commit if changed" guard triggered
`"Calendar unchanged; skipping commit."` on every subsequent run.
GitHub Pages was never re-invoked, and the live site stayed on the
1 Jul snapshot for 2+ days while `main` was correct. A booking added
on 2 Jul (`HMNN4KTXSY`, EA, 7–13 Jul) was missing from the live
calendar until manually rebuilt.

## Decision

The publish workflow now blocks on GitHub Pages actually reaching
`built` status:

1. Read `pages` and `pages/builds/latest` status via the GitHub API.
2. If either is `errored`, request a rebuild
   (`POST /repos/{owner}/{repo}/pages/builds`).
3. Poll for up to ~10 minutes; fail the workflow if the latest build
   ends in `errored` or the poll times out.

This runs on **every** workflow invocation, not only when the calendar
content changed — so a Pages error from a previous run gets healed on
the next schedule tick even if no bookings moved.

We also added `docs/.nojekyll` to opt out of Jekyll processing.
`docs/index.html` is a fully-formed static page; there is no benefit
to running Jekyll over it, and it removes one class of transient
build failure.

## Consequences

- No more silent stale-site drift. The workflow fails loudly when
  Pages is stuck, instead of appearing green.
- Workflow runtime grows by up to ~10 minutes on the failure path.
  On the happy path the added step is a handful of API calls
  (<15 s), which is acceptable given the 6-hourly cron cadence.
- The workflow now requires `pages: write` permission.
- Reverting is cheap: drop the "Verify GitHub Pages deployment"
  step. `.nojekyll` can stay regardless.
