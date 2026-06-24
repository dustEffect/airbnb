# Reseed Chrome profile for GitHub Actions

> Maintainer docs for `scripts/reseed-chrome-profile.sh` and `scripts/seed-chrome-profile-local.sh`. Not published on GitHub Pages (`docs/` is only the calendar site).

GitHub Actions cannot complete Airbnb **2FA** on its own. This project stores a **logged-in Linux Chrome profile** in the Actions cache so `publish-calendar.yml` can open the multicalendar headlessly.

Use this guide when:

- Setting up CI for the first time
- `publish-calendar.yml` fails because Airbnb logged out or the session expired
- You changed your Airbnb password or revoked browser sessions

For normal calendar updates you only need:

```bash
gh workflow run publish-calendar.yml --repo dustEffect/airbnb
```

You do **not** need to reseed for every HTML refresh.

---

## One-command reseed (recommended)

From the repo root, in an **interactive terminal** (Terminal.app or the Cursor integrated terminal — not a background task), with Docker Desktop running and `gh` authenticated:

```bash
./scripts/reseed-chrome-profile.sh
```

Optional: verify prerequisites and Docker → XQuartz display forwarding before the full flow (~15 s):

```bash
./scripts/reseed-chrome-profile.sh --preflight
```

That script:

1. Opens Linux Chrome in Docker on your Mac (you complete login + 2FA)
2. Packages `profiles/calendar-airbnb` and uploads it to a **temporary** GitHub release
3. Runs the `Seed Chrome profile cache` workflow (copies profile into Actions cache)
4. Runs `publish-calendar.yml` to verify CI can use the profile
5. **Deletes** the public release (contains live session cookies)

Options:

```bash
./scripts/reseed-chrome-profile.sh --local-only    # Docker login + upload only
./scripts/reseed-chrome-profile.sh --ci-only       # CI steps only (release already uploaded)
./scripts/reseed-chrome-profile.sh --skip-fetch    # seed cache only, skip calendar publish
./scripts/reseed-chrome-profile.sh --skip-cleanup  # keep release (not recommended)
./scripts/reseed-chrome-profile.sh --preflight     # check Docker, gh, XQuartz display only
```

Override repo: `GITHUB_REPOSITORY=owner/repo ./scripts/reseed-chrome-profile.sh`

---

## Before you run

Quick checklist (all must pass):

| Check | How |
|-------|-----|
| Docker Desktop running | `docker info` |
| `gh` logged in | `gh auth status` |
| Airbnb credentials | `credentials.local.env` exists |
| XQuartz installed | `test -x /opt/X11/bin/xhost` |
| Interactive terminal | Run `./scripts/reseed-chrome-profile.sh` directly — do **not** pipe to `tee` or run from a non-TTY automation context for step 1 |

The login step opens a **Linux Chrome window** on your Mac via XQuartz. Complete Airbnb login and 2FA there, then wait for the browser to close on its own.

If XQuartz was just installed or updated, **log out and back in** once before the first reseed.

---

## Prerequisites (macOS)

Install once:

| Tool | Purpose | Install |
|------|---------|---------|
| Docker Desktop | Run Linux Chrome | [docker.com](https://www.docker.com/products/docker-desktop/) |
| XQuartz | Show Docker Chrome on your screen | `brew install --cask xquartz` then **log out and back in** |
| GitHub CLI | Upload archive and trigger workflows | `brew install gh` then `gh auth login` |
| `credentials.local.env` | Airbnb email/password for the browser | `cp credentials.local.env.example credentials.local.env` |

GitHub repository secrets (for CI, not the local script):

- `AIRBNB_EMAIL`
- `AIRBNB_PASSWORD`

---

## What happens under the hood

```
┌─────────────────────────────────────────────────────────────────┐
│ Your Mac                                                         │
│  ./scripts/reseed-chrome-profile.sh                              │
│    → Docker (linux/amd64) + Playwright Chrome + --gui            │
│    → you log in to Airbnb + complete 2FA                         │
│    → profiles/calendar-airbnb/  (Linux Chrome user data)         │
│    → chrome-profile.tar.gz → temporary GitHub release            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ GitHub Actions                                                   │
│  seed-chrome-profile.yml                                         │
│    → download release → extract profile → save Actions cache     │
│  publish-calendar.yml (optional verification)                               │
│    → restore cache → fetch bookings → publish calendar           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    Delete chrome-profile-seed release
                    (profile stays in Actions cache only)
```

Why **Linux** Chrome in Docker? CI runs on `ubuntu-latest`. A macOS Chrome profile is not portable to Linux.

Why **linux/amd64** on Apple Silicon? Playwright’s Google Chrome build is not available for Linux ARM64.

---

## Manual step-by-step

If you prefer to run each step yourself:

### 1. Local login and upload

```bash
./scripts/seed-chrome-profile-local.sh
```

A Chrome window opens inside Docker. Log into Airbnb and finish 2FA. When the browser closes, the script packages the profile and uploads `chrome-profile.tar.gz` to the `chrome-profile-seed` release.

### 2. Seed Actions cache

```bash
gh workflow run seed-chrome-profile.yml --repo dustEffect/airbnb
gh run watch --repo dustEffect/airbnb "$(gh run list --repo dustEffect/airbnb --workflow seed-chrome-profile.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
```

### 3. Verify with a fetch (optional but recommended)

```bash
gh workflow run publish-calendar.yml --repo dustEffect/airbnb
gh run watch --repo dustEffect/airbnb "$(gh run list --repo dustEffect/airbnb --workflow publish-calendar.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
```

### 4. Delete the release (security)

The release contains **live session cookies**. Delete it as soon as the seed workflow succeeds:

```bash
gh release delete chrome-profile-seed --repo dustEffect/airbnb --yes
```

---

## Security

- The seed archive is a **logged-in browser session**. Anyone who downloads it can access your Airbnb account until the session expires.
- Use a **private** repository, or delete the release within minutes.
- Never commit `profiles/` or `chrome-profile.tar.gz` (both are gitignored).
- After reseeding, you do not need the release; the profile lives in the Actions cache (`airbnb-chrome-profile-*` keys).

---

## Troubleshooting

### `the input device is not a TTY`

Docker needs a pseudo-terminal for the login container. Run the reseed in **Terminal.app** or the Cursor **integrated terminal**:

```bash
cd /path/to/airbnb
./scripts/reseed-chrome-profile.sh
```

Do not run step 1 from a background job or a tool that cannot allocate a TTY. If you already uploaded the profile (`--local-only`), finish with:

```bash
./scripts/reseed-chrome-profile.sh --ci-only
```

### `Authorization required, but no authorization protocol specified`

XQuartz is running but Docker is not allowed to connect yet. Run this once, then rerun the reseed:

```bash
open -a XQuartz
sleep 2
export DISPLAY=:0
/opt/X11/bin/xhost +localhost
/opt/X11/bin/xhost +
```

Also confirm XQuartz → **Settings → Security** → **Allow connections from network clients** is enabled, then quit and reopen XQuartz if needed.

Verify display forwarding before the full reseed:

```bash
./scripts/reseed-chrome-profile.sh --preflight
```

You should see `Docker → XQuartz display: OK`.

### `xhost: command not found`

XQuartz is installed but `/opt/X11/bin` is not on `PATH` yet. Open a **new terminal** or run:

```bash
export PATH="/opt/X11/bin:$PATH"
```

### `unable to open display` / headed browser without XServer

1. Run the **Authorization required** fix in the section above.
2. Ensure TCP is enabled (the script sets this automatically):

   ```bash
   defaults write org.xquartz.X11 nolisten_tcp -bool false
   ```

   Then quit and reopen XQuartz, or rerun the script (it restarts XQuartz for you).

3. In XQuartz → **Settings → Security**, enable **Allow connections from network clients**.
4. Confirm port 6000 is listening: `lsof -iTCP:6000 -sTCP:LISTEN`
5. If it still fails after a fresh XQuartz install, **log out and back in** once.

### `ERROR: not supported on Linux Arm64`

You are on Apple Silicon and Docker pulled an ARM image. The script forces `--platform linux/amd64`; make sure you run the current version of `seed-chrome-profile-local.sh`.

### `Cache save failed` in publish-calendar.yml

Harmless if the seed workflow already populated the cache. Newer workflow versions save under `airbnb-chrome-profile-<run_id>` so each run can update the profile without conflicting with an existing key.

### CI still cannot log in after reseeding

- Confirm `seed-chrome-profile.yml` succeeded and logs show the profile extracted (~60 MB).
- Confirm `AIRBNB_EMAIL` / `AIRBNB_PASSWORD` secrets are set on the repo.
- Reseed again; Airbnb may have invalidated the session during upload.

### `chrome-profile-seed` git tag remains after cleanup

`gh release delete` removes the release assets but may leave the tag. That is harmless. Delete manually if you want:

```bash
gh api -X DELETE "repos/dustEffect/airbnb/git/refs/tags/chrome-profile-seed"
```

---

## Day-to-day operations

| Task | Command |
|------|---------|
| Refresh calendar (normal) | `gh workflow run publish-calendar.yml --repo dustEffect/airbnb` |
| Reseed Chrome session | `./scripts/reseed-chrome-profile.sh` |
| Check reseed prerequisites | `./scripts/reseed-chrome-profile.sh --preflight` |
| Local HTML preview | `./calendar.sh` |

The scheduled `publish-calendar.yml` cron (05:00, 11:00, 17:00, 23:00 Lisbon / 04:00, 10:00, 16:00, 22:00 UTC) uses the cached profile automatically.
