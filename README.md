# Airbnb scripts

Personal automation for an Airbnb multicalendar: fetch reservations, format checkout summaries, and build a cleaning calendar spreadsheet.

## Pipelines

| Script | Purpose |
|--------|---------|
| `./fetch.sh` | Log into Airbnb and write `shared/bookings.json` |
| `./checkouts.sh` | Fetch (optional) and write `checkouts/checkouts.txt` |
| `./cleanings.sh` | Fetch (optional) and update `cleanings/templates/cleanings-map.xlsx` |

All pipelines share the same bookings file: `shared/bookings.json`.

```
fetch ──► shared/bookings.json ──► checkouts/checkouts.txt
                              └──► cleanings calendar sheet
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
./cleanings.sh                      # fetch full calendar year + update workbook
./cleanings.sh --no-fetch           # reuse existing shared/bookings.json
./cleanings.sh --year 2026 --no-fetch
```

The Excel template lives at `cleanings/templates/cleanings-map.xlsx`. Each run clones the `template` sheet into a year-named sheet (e.g. `2026`).

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
cleanings/       Excel cleaning calendar (template in templates/)
shared/          Paths and listing label mapping
```

## Outputs (gitignored)

- `shared/bookings.json`
- `checkouts/checkouts.txt`
- `profiles/` (Chrome user data)
- `credentials.local.env`
