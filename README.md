# Airbnb scripts

Personal automation for an Airbnb multicalendar: fetch reservations, format checkout summaries, and build a stay calendar HTML page.

## Pipelines

| Script | Purpose |
|--------|---------|
| `./fetch.sh` | Log into Airbnb and write `shared/bookings.json` |
| `./checkouts.sh` | Fetch (optional) and write `checkouts/checkouts.txt` |
| `./calendar.sh` | Fetch (optional) and write `calendars/templates/calendar-{year}.html` |
| `./notify` (CI) | Send morning/afternoon booking push notifications |

All pipelines share the same bookings file: `shared/bookings.json`.

```
fetch ──► shared/bookings.json ──► checkouts/checkouts.txt
                              └──► stay calendar (html)
```

## Setup

```bash
cd /path/to/airbnb
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/playwright install chromium
```

Copy credentials:

```bash
cp credentials.local.env.example credentials.local.env
# Edit AIRBNB_EMAIL and AIRBNB_PASSWORD
```

`credentials.local.env` is gitignored. Use single quotes around the password if it contains special characters.

## Usage

### Fetch bookings only

```bash
./fetch.sh
./fetch.sh --gui                    # visible Chrome window
./fetch.sh --months 6 --from-month 2026-06
```

### Checkout summary

```bash
./checkouts.sh                      # fetch + write checkouts/checkouts.txt
./checkouts.sh --no-fetch           # reuse existing shared/bookings.json
./checkouts.sh --diff --no-fetch    # print changes from tomorrow, then update file
```

### Stay calendar

```bash
./calendar.sh                      # fetch full calendar year + write HTML
./calendar.sh --no-fetch           # reuse existing shared/bookings.json
./calendar.sh --year 2026 --no-fetch
```

Each run writes a browser-viewable calendar at `calendars/templates/calendar-{year}.html` with the five listings and stay windows. When run from the default output directory, it also copies to `docs/index.html` for GitHub Pages.

### Console entry points

After `pip install -e .`:

```bash
airbnb-fetch
airbnb-checkouts
airbnb-calendar
airbnb-notify morning --snapshot docs/bookings-snapshot.json
airbnb-vapid-keys
```

## Booking push notifications

Android notifications for today's check-ins (07:00 Lisbon) and
tomorrow's check-ins and check-outs (17:30 Lisbon in summer). See
[`docs/adr/0002-booking-push-notifications.md`](docs/adr/0002-booking-push-notifications.md).

### One-time setup

1. Generate VAPID keys:

```bash
.venv/bin/pip install -e .
.venv/bin/python -m notifications.vapid_keys
```

2. Add GitHub Actions secrets:

| Secret | Value |
|--------|-------|
| `VAPID_PUBLIC_KEY` | Public key from step 1 |
| `VAPID_PRIVATE_KEY` | Private key from step 1 |
| `VAPID_SUBJECT` | `mailto:your@email.com` |
| `PUSH_SUBSCRIPTIONS` | JSON array of push subscriptions (one per phone) |

3. Publish the calendar so the PWA embeds the public key
   (`publish-calendar.yml` passes `VAPID_PUBLIC_KEY` when building).

4. On each phone: open the installed PWA → **Ativar notificações** →
   **Subscrever** → grant permission → **Copiar JSON** → add each
   subscription object to the `PUSH_SUBSCRIPTIONS` array in GitHub
   secrets.

Example `PUSH_SUBSCRIPTIONS`:

```json
[
  {"endpoint": "…", "keys": {"p256dh": "…", "auth": "…"}},
  {"endpoint": "…", "keys": {"p256dh": "…", "auth": "…"}}
]
```

### Manual send (CI)

```bash
gh workflow run notify-bookings.yml --repo dustEffect/airbnb -f kind=morning
gh workflow run notify-bookings.yml --repo dustEffect/airbnb -f kind=afternoon
```

## Tests

```bash
.venv/bin/pytest
```

## Project layout

```
fetch/           Airbnb browser automation and bookings extraction
checkouts/       Checkout text formatting
calendars/       HTML stay calendar (`calendars`, not `calendar`, avoids Python stdlib name clash)
notifications/   Booking push notification formatting and delivery
shared/          Paths and listing label mapping
```

## GitHub Actions (stay calendar)

The calendar at `docs/index.html` is published by `publish-calendar.yml` (four times daily + manual dispatch):

```bash
gh workflow run publish-calendar.yml --repo dustEffect/airbnb
```

CI needs a **logged-in Linux Chrome profile** in the Actions cache (Airbnb 2FA cannot be done headlessly in Actions). Reseed when the session expires:

```bash
./scripts/reseed-chrome-profile.sh
```

See **[scripts/seed-chrome-profile.md](scripts/seed-chrome-profile.md)** for prerequisites (Docker, XQuartz, `gh`), troubleshooting, and security notes.

### Failure alerts

Enable [GitHub notification settings](https://github.com/settings/notifications) → **Actions** → **Send notifications for failed workflows only**.

## Outputs (gitignored)

- `shared/bookings.json`
- `checkouts/checkouts.txt`
- `calendars/templates/calendar-*.html`
- `profiles/` (Chrome user data)
- `chrome-profile.tar.gz` (temporary seed archive)
- `credentials.local.env`
