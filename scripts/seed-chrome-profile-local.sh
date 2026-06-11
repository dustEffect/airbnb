#!/usr/bin/env bash
# Create a Linux Chrome profile (login + 2FA in Docker) and upload it for the seed workflow.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${GITHUB_REPOSITORY:-dustEffect/airbnb}"
ARCHIVE="$ROOT/chrome-profile.tar.gz"
PLAYWRIGHT_IMAGE="${PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright:v1.49.0-jammy}"

cd "$ROOT"

if [[ ! -f credentials.local.env ]]; then
  echo "Missing credentials.local.env — copy from credentials.local.env.example first." >&2
  exit 1
fi

if ! command -v docker >/dev/null; then
  echo "Docker is required. Install Docker Desktop and try again." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Start Docker Desktop and try again." >&2
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  if ! command -v xhost >/dev/null; then
    echo "Install XQuartz first: brew install --cask xquartz" >&2
    echo "Then log out/in, run: open -a XQuartz && xhost +localhost" >&2
    exit 1
  fi
  xhost +localhost >/dev/null 2>&1 || true
  DISPLAY_ARG="-e DISPLAY=host.docker.internal:0"
else
  DISPLAY_ARG="-e DISPLAY=${DISPLAY:-:0}"
fi

echo "Opening Linux Chrome — complete Airbnb login and 2FA in the browser window."
echo

docker run -it --rm \
  $DISPLAY_ARG \
  -v "$ROOT:/work" -w /work \
  "$PLAYWRIGHT_IMAGE" \
  bash -lc '
    set -euo pipefail
    apt-get update -qq
    apt-get install -y -qq python3-venv python3-pip >/dev/null
    python3 -m venv /tmp/seed-venv
    /tmp/seed-venv/bin/pip install -q -e .
    /tmp/seed-venv/bin/playwright install chrome
    /tmp/seed-venv/bin/python -m fetch.main --gui
  '

if [[ ! -d profiles/calendar-airbnb ]]; then
  echo "Profile not found at profiles/calendar-airbnb — login may have failed." >&2
  exit 1
fi

echo
echo "Packaging profile..."
rm -f "$ARCHIVE"
tar czf "$ARCHIVE" -C profiles calendar-airbnb
ls -lh "$ARCHIVE"

if ! command -v gh >/dev/null; then
  echo "Install GitHub CLI (gh) to upload the seed archive." >&2
  exit 1
fi

echo
echo "Uploading to GitHub release chrome-profile-seed..."
if gh release view chrome-profile-seed --repo "$REPO" >/dev/null 2>&1; then
  gh release upload chrome-profile-seed "$ARCHIVE" --repo "$REPO" --clobber
else
  gh release create chrome-profile-seed "$ARCHIVE" \
    --repo "$REPO" \
    --title "Chrome profile seed" \
    --notes "Temporary archive for seeding Actions cache. Safe to delete after seeding."
fi

echo
echo "Done. Next steps:"
echo "  1. gh workflow run seed-chrome-profile.yml --repo $REPO"
echo "  2. gh workflow run fetch.yml --repo $REPO"
echo "  3. Optional cleanup: gh release delete chrome-profile-seed --repo $REPO --yes"
