# Domain glossary

Canonical vocabulary for this repo. Prefer these terms in code, commits,
docs, and conversation. If a term here disagrees with the code, the code
is wrong (or this file is stale — fix one of them).

## Listing

An apartment we rent out on Airbnb. Each listing has:

- A long Airbnb name (e.g. `"T1 Renovado c/ metro à porta"`).
- A **short code**, one of: `T0`, `T1`, `T2`, `EA`, `EB`.

The authoritative long-name → short-code mapping lives in
[`shared/listing_labels.py`](shared/listing_labels.py). Display order is
`T0, T1, T2, EA, EB`.

Do not identify listings by numeric `listingId` in user-facing output —
use the short code.

## Booking

A period of time a guest occupies one of our listings.

**Synonyms:** `stay`, `reservation`. All three mean the same thing and
appear in the codebase (`bookings.json`, HTML `stay-*` classes, Airbnb
"reservation" status strings). Prefer **booking** in new code and docs.

A booking is a reservation of a listing for a period. It exists
independently of the guest — do not model it as "host-facing" or
"guest-facing".

## Custom stay

A booking added manually in the browser, not sourced from Airbnb.
Stored in `localStorage` only; never synced back to Airbnb. Rendered
with the `stay-custom` CSS class.

## Publish (the calendar)

The end-to-end act of making the current calendar HTML live on GitHub
Pages. Covers the full pipeline:

1. Fetch bookings from Airbnb
2. Render `docs/index.html`
3. Commit and push to `main`
4. GitHub Pages serves the new HTML

Publishing is **not complete** until the live site actually serves the
new content. A green CI run that ends at step 3 has not published.

## Build (the calendar)

Loose synonym for **publish**; occasionally used for just the
fetch-and-render half (steps 1–2). Prefer **publish** when the intent
is the whole pipeline.

## Deploy

Reserved for *code* deployment. **Never** use "deploy" to refer to the
calendar pipeline — say **publish** instead.
