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

### What goes where

Web Push needs **two kinds** of secrets. They come from **different places**:

| GitHub secret | What it is | Where you get it |
|---------------|------------|------------------|
| `VAPID_PUBLIC_KEY` | Server identity (public half) | **Terminal, once** — see step 1 below |
| `VAPID_PRIVATE_KEY` | Server identity (private half) | **Terminal, once** — same command; never put this in the app |
| `VAPID_SUBJECT` | Contact for the push service | You choose, e.g. `mailto:you@example.com` |
| `PUSH_SUBSCRIPTIONS` | One JSON object **per phone** | **PWA button, per device** — see step 4 below |

The calendar's **Ativar notificações** button only helps with `PUSH_SUBSCRIPTIONS`
(phone subscriptions). It does **not** generate VAPID keys — the private key must
stay off the phone and out of the browser.

### Setup (one time + per phone)

#### 1. Generate VAPID keys (laptop, once)

On your computer — not in the PWA:

```bash
.venv/bin/pip install -e .
airbnb-vapid-keys
```

Copy the printed `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY` (multi-line PEM is fine).

#### 2. Add GitHub Actions secrets

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret | Value |
|--------|-------|
| `VAPID_PUBLIC_KEY` | Single line from step 1 |
| `VAPID_PRIVATE_KEY` | Full PEM block from step 1 (including `BEGIN` / `END` lines) |
| `VAPID_SUBJECT` | `mailto:your@email.com` |
| `PUSH_SUBSCRIPTIONS` | Start with `[]` — you fill this in step 4 |

Or via CLI:

```bash
gh secret set VAPID_PUBLIC_KEY --repo dustEffect/airbnb
gh secret set VAPID_PRIVATE_KEY --repo dustEffect/airbnb
gh secret set VAPID_SUBJECT --repo dustEffect/airbnb
gh secret set PUSH_SUBSCRIPTIONS --repo dustEffect/airbnb --body '[]'
```

#### 3. Publish the calendar (embeds the public key)

The publish workflow passes `VAPID_PUBLIC_KEY` into the calendar build so the PWA
can subscribe. Run it once after step 2:

```bash
gh workflow run publish-calendar.yml --repo dustEffect/airbnb
```

Wait until the workflow finishes and GitHub Pages serves the new HTML. Until this
runs, the PWA shows **Notificações não configuradas** and subscribe is disabled.

#### 4. Register each phone (PWA button)

Repeat on **each** Android phone:

1. Open the installed PWA (**Mapa de Estadias** from the home screen — not only a browser tab).
2. Tap **Ativar notificações** under the page title.
3. Tap **Subscrever** and allow notifications when Android asks.
4. Tap **Copiar JSON** — this is one phone's subscription, **not** a VAPID key.
5. In GitHub, edit `PUSH_SUBSCRIPTIONS`: add the copied object to the JSON array.

Example after registering two phones:

```json
[
  {
    "endpoint": "https://fcm.googleapis.com/fcm/send/…",
    "keys": { "p256dh": "…", "auth": "…" }
  },
  {
    "endpoint": "https://fcm.googleapis.com/fcm/send/…",
    "keys": { "p256dh": "…", "auth": "…" }
  }
]
```

Re-copy and update GitHub only if you reinstall the PWA or revoke notification permission on that phone.

#### 5. Verify

```bash
gh workflow run notify-bookings.yml --repo dustEffect/airbnb -f kind=morning
```

If there are check-ins today, both phones should receive a notification. Empty days send nothing.

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
