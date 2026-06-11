#!/usr/bin/env bash
# Create a Linux Chrome profile (login + 2FA in Docker) and upload it for the seed workflow.
#
# Usually run via the full orchestrator:
#   ./scripts/reseed-chrome-profile.sh
#
# Full documentation: scripts/seed-chrome-profile.md
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

_xquartz_listens_tcp() {
  lsof -iTCP:6000 -sTCP:LISTEN >/dev/null 2>&1
}

_restart_xquartz() {
  echo "Restarting XQuartz so Docker can connect on TCP port 6000..."
  osascript -e 'quit app "XQuartz"' 2>/dev/null || true
  sleep 1
  open -a XQuartz
  for _ in {1..40}; do
    pgrep -qx Xquartz && _xquartz_listens_tcp && return 0
    sleep 0.5
  done
  return 1
}

if [[ "$(uname -s)" == "Darwin" ]]; then
  XHOST="$(command -v xhost 2>/dev/null || true)"
  if [[ -z "$XHOST" && -x /opt/X11/bin/xhost ]]; then
    XHOST=/opt/X11/bin/xhost
    export PATH="/opt/X11/bin:$PATH"
  fi
  if [[ -z "$XHOST" ]]; then
    echo "Install XQuartz first: brew install --cask xquartz" >&2
    echo "Then log out/in and run this script again." >&2
    exit 1
  fi
  if [[ "$(defaults read org.xquartz.X11 nolisten_tcp 2>/dev/null || echo 1)" == "1" ]]; then
    echo "Enabling XQuartz TCP connections for Docker..."
    defaults write org.xquartz.X11 nolisten_tcp -bool false
    _restart_xquartz || true
  elif ! _xquartz_listens_tcp; then
    _restart_xquartz || true
  elif ! pgrep -qx Xquartz; then
    echo "Starting XQuartz..."
    open -a XQuartz
    for _ in {1..40}; do
      pgrep -qx Xquartz && _xquartz_listens_tcp && break
      sleep 0.5
    done
  fi
  if ! pgrep -qx Xquartz; then
    echo "XQuartz did not start. Open it manually: open -a XQuartz" >&2
    exit 1
  fi
  if ! _xquartz_listens_tcp; then
    echo "XQuartz is not listening on TCP port 6000." >&2
    echo "Open XQuartz → Settings → Security → enable \"Allow connections from network clients\"," >&2
    echo "then quit XQuartz and run this script again." >&2
    exit 1
  fi
  export DISPLAY="${DISPLAY:-:0}"
  if ! "$XHOST" +localhost 2>/dev/null; then
    echo "xhost failed (DISPLAY=$DISPLAY). Try in your shell:" >&2
    echo "  open -a XQuartz && export DISPLAY=:0 && /opt/X11/bin/xhost +localhost" >&2
    exit 1
  fi
  DISPLAY_ARG="-e DISPLAY=host.docker.internal:0"
  echo "Checking Docker → XQuartz display forwarding..."
  if ! docker run --rm --platform linux/amd64 $DISPLAY_ARG \
    "$PLAYWRIGHT_IMAGE" \
    bash -lc 'apt-get update -qq && apt-get install -y -qq x11-utils >/dev/null && xdpyinfo >/dev/null'; then
    echo "Docker cannot open the Mac display." >&2
    echo "Try: quit XQuartz, run this script again, or manually:" >&2
    echo "  /opt/X11/bin/xhost +localhost" >&2
    exit 1
  fi
else
  DISPLAY_ARG="-e DISPLAY=${DISPLAY:-:0}"
fi

echo "Opening Linux Chrome — complete Airbnb login and 2FA in the browser window."
if [[ "$(uname -m)" == "arm64" ]]; then
  echo "(Apple Silicon: using linux/amd64 container — Playwright Chrome is not available on Linux ARM64.)"
fi
echo

docker run -it --rm \
  --platform linux/amd64 \
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
echo "Local seed uploaded. To finish CI setup:"
echo "  ./scripts/reseed-chrome-profile.sh --ci-only"
echo
echo "Or next time run the full flow in one go:"
echo "  ./scripts/reseed-chrome-profile.sh"
