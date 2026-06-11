# Airbnb scripts

Personal automation for an Airbnb multicalendar: fetch reservations, format checkout summaries, and build a cleaning calendar HTML page.

## Pipelines

| Script | Purpose |
|--------|---------|
| `./fetch.sh` | Log into Airbnb and write `shared/bookings.json` |
| `./checkouts.sh` | Fetch (optional) and write `checkouts/checkouts.txt` |
| `./cleanings.sh` | Fetch (optional) and write `cleanings/templates/cleanings-{year}.html` |

All pipelines share the same bookings file: `shared/bookings.json`.

```
fetch ──► shared/bookings.json ──► checkouts/checkouts.txt
                              └──► cleanings calendar (html)
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

### Cleaning calendar

```bash
./cleanings.sh                      # fetch full calendar year + write HTML
./cleanings.sh --no-fetch           # reuse existing shared/bookings.json
./cleanings.sh --year 2026 --no-fetch
```

Each run writes a browser-viewable calendar at `cleanings/templates/cleanings-{year}.html` with the five listings and stay windows. To publish on GitHub Pages, copy it to `docs/index.html` and push.

### Console entry points

After `pip install -e .`, these are also available:

```bash
airbnb-fetch
airbnb-checkouts
airbnb-cleanings
```

Or via Python modules:

```bash
.venv/bin/python -m fetch.main
.venv/bin/python -m checkouts.main
.venv/bin/python -m cleanings.main
```

## Tests

```bash
.venv/bin/pytest
```

## Project layout

```
fetch/           Airbnb browser automation and bookings extraction
checkouts/       Checkout text formatting
cleanings/       HTML cleaning calendar
shared/          Paths and listing label mapping
```

## GitHub Actions (cleaning calendar)

The calendar at `docs/index.html` is published by `publish-cleaning-calendar.yml` (daily cron + manual dispatch):

```bash
gh workflow run publish-cleaning-calendar.yml --repo dustEffect/airbnb
```

CI needs a **logged-in Linux Chrome profile** in the Actions cache (Airbnb 2FA cannot be done headlessly in Actions). Reseed when the session expires:

```bash
./scripts/reseed-chrome-profile.sh
```

See **[docs/seed-chrome-profile.md](docs/seed-chrome-profile.md)** for prerequisites (Docker, XQuartz, `gh`), troubleshooting, and security notes.

## Outputs (gitignored)

- `shared/bookings.json`
- `checkouts/checkouts.txt`
- `cleanings/templates/cleanings-*.html`
- `profiles/` (Chrome user data)
- `chrome-profile.tar.gz` (temporary seed archive)
- `credentials.local.env`
