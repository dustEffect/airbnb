# 2. Booking push notifications via Web Push

Date: 2026-07-05

## Status

Accepted.

## Context

The host wants Android notifications about upcoming check-ins and
check-outs without opening the calendar PWA every day:

- **Morning (07:00 Lisbon):** today's check-ins (`startDate == today`).
- **Afternoon (17:00 Lisbon):** tomorrow's check-ins and check-outs.

The calendar PWA already embeds booking data in published HTML, and
`shared/bookings.json` is gitignored. Pure client-side scheduled
notifications cannot fire at exact times when the app is never opened —
service workers on Android do not guarantee delayed timers, and
Notification Triggers was removed from Chrome.

Custom stays (`localStorage` only) cannot be included in server-side
notifications.

## Decision

Use **server Web Push as an alarm clock**, not as a live-data channel:

1. **Publish pipeline** writes a slim `docs/bookings-snapshot.json`
   (listing code, dates, guest first name) alongside `docs/index.html`.
   Data freshness matches the calendar (up to four fetches per day).

2. **`notify-bookings.yml`** runs at `06:00` and `16:30` UTC
   (07:00 / 17:30 Lisbon in summer; one hour earlier in winter — accepted
   drift). The afternoon job starts 30 minutes after the publish cron at
   `16:00` UTC so the committed snapshot is usually fresh. It reads the
   snapshot, formats the message, and sends Web Push via `pywebpush` to every entry in the
   `PUSH_SUBSCRIPTIONS` GitHub secret (JSON array for multiple phones).

3. **PWA onboarding:** the calendar page exposes "Ativar notificações".
   Each phone subscribes with the VAPID public key embedded at build
   time; the user copies the subscription JSON into
   `PUSH_SUBSCRIPTIONS`.

4. **Message rules:** compact Portuguese copy; no turnover warning icon;
   **silence on empty days** (no push sent).

5. **Scope:** Airbnb bookings only — custom stays stay in the calendar
   UI but are excluded from push.

## Consequences

- Notifications work when the app is not opened, as long as publish CI
  has run recently enough for the snapshot to be useful.
- Requires GitHub secrets: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
  `VAPID_SUBJECT`, `PUSH_SUBSCRIPTIONS`.
- Guest first names appear in the committed snapshot (private repo
  assumption).
- Winter cron drift shifts notifications one hour earlier; exact
  year-round Lisbon time would need dual crons with date guards.
- Re-subscribe after reinstalling the PWA or revoking notification
  permission.

## Alternatives considered

| Alternative | Why not |
|---|---|
| ntfy / Telegram | User preferred Web Push integrated with the existing PWA |
| Local schedule only | Unreliable without opening the app |
| Read gitignored `bookings.json` in notify CI | File is not in the repository |
| Parse `docs/index.html` in notify CI | Fragile; snapshot is explicit and small |
