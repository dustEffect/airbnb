#!/usr/bin/env bash
# Reseed the logged-in Linux Chrome profile used by GitHub Actions CI.
#
# Full guide: scripts/seed-chrome-profile.md
#
# Typical usage (from repo root):
#   ./scripts/reseed-chrome-profile.sh
#
# Options:
#   --local-only     Create profile and upload release only; skip CI workflows
#   --ci-only        Skip local Docker login; run CI workflows (release must exist)
#   --skip-fetch     Seed cache but do not run publish-calendar.yml afterwards
#   --skip-cleanup   Do not delete the temporary GitHub release (not recommended)
#   --preflight      Check Docker, gh, credentials, and XQuartz display; then exit
#   -h, --help       Show this help
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${GITHUB_REPOSITORY:-dustEffect/airbnb}"
LOCAL_SCRIPT="$ROOT/scripts/seed-chrome-profile-local.sh"

LOCAL_ONLY=0
CI_ONLY=0
SKIP_FETCH=0
SKIP_CLEANUP=0
PREFLIGHT_ONLY=0

usage() {
  sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
  echo
  echo "Environment:"
  echo "  GITHUB_REPOSITORY   Target repo (default: dustEffect/airbnb)"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local-only) LOCAL_ONLY=1 ;;
    --ci-only) CI_ONLY=1 ;;
    --skip-fetch) SKIP_FETCH=1 ;;
    --skip-cleanup) SKIP_CLEANUP=1 ;;
    --preflight) PREFLIGHT_ONLY=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if [[ ! -x "$LOCAL_SCRIPT" ]]; then
  echo "Missing executable: $LOCAL_SCRIPT" >&2
  exit 1
fi

if ! command -v gh >/dev/null && [[ "$LOCAL_ONLY" -eq 0 ]]; then
  echo "GitHub CLI (gh) is required. Install with: brew install gh" >&2
  echo "Or run with --local-only and trigger workflows manually." >&2
  exit 1
fi

_wait_for_workflow() {
  local workflow_file="$1"
  local label="$2"
  echo
  echo "Waiting for $label to finish..."
  sleep 4
  local run_id
  run_id="$(gh run list --repo "$REPO" --workflow "$workflow_file" --limit 1 --json databaseId --jq '.[0].databaseId')"
  if [[ -z "$run_id" || "$run_id" == "null" ]]; then
    echo "Could not find a run for $workflow_file" >&2
    exit 1
  fi
  gh run watch "$run_id" --repo "$REPO" --exit-status
}

if [[ "$LOCAL_ONLY" -eq 1 && "$CI_ONLY" -eq 1 ]]; then
  echo "Choose either --local-only or --ci-only, not both." >&2
  exit 1
fi

_preflight() {
  local failed=0
  echo "== Preflight =="
  if [[ ! -f "$ROOT/credentials.local.env" ]]; then
    echo "✗ Missing credentials.local.env" >&2
    failed=1
  else
    echo "✓ credentials.local.env"
  fi
  if ! command -v docker >/dev/null; then
    echo "✗ Docker not installed" >&2
    failed=1
  elif ! docker info >/dev/null 2>&1; then
    echo "✗ Docker daemon not running — start Docker Desktop" >&2
    failed=1
  else
    echo "✓ Docker"
  fi
  if [[ "$PREFLIGHT_ONLY" -eq 1 || "$CI_ONLY" -eq 0 && "$LOCAL_ONLY" -eq 0 ]] || [[ "$LOCAL_ONLY" -eq 1 ]]; then
    if [[ "$(uname -s)" == "Darwin" ]] && ! { test -x /opt/X11/bin/xhost || command -v xhost >/dev/null; }; then
      echo "✗ XQuartz not installed (brew install --cask xquartz)" >&2
      failed=1
    elif [[ "$(uname -s)" == "Darwin" ]]; then
      echo "✓ XQuartz (xhost)"
    fi
  fi
  if [[ "$PREFLIGHT_ONLY" -eq 1 || ( "$CI_ONLY" -eq 0 && "$LOCAL_ONLY" -eq 0 ) ]] || [[ "$LOCAL_ONLY" -eq 1 ]]; then
    if ! [[ -t 0 ]]; then
      if [[ "$PREFLIGHT_ONLY" -eq 1 ]]; then
        echo "⚠ Not an interactive terminal (needed for Chrome login during reseed)"
      else
        echo "✗ Not an interactive terminal — use Terminal.app or Cursor integrated terminal" >&2
        failed=1
      fi
    else
      echo "✓ Interactive terminal"
    fi
  fi
  if [[ "$CI_ONLY" -eq 0 ]]; then
    if ! command -v gh >/dev/null; then
      echo "✗ GitHub CLI (gh) not installed" >&2
      failed=1
    elif ! gh auth status >/dev/null 2>&1; then
      echo "✗ gh not authenticated — run: gh auth login" >&2
      failed=1
    else
      echo "✓ gh authenticated"
    fi
  fi
  if [[ "$failed" -ne 0 ]]; then
    echo
    echo "Fix the issues above, then rerun. See scripts/seed-chrome-profile.md" >&2
    exit 1
  fi
  if [[ "$(uname -s)" == "Darwin" && ( "$PREFLIGHT_ONLY" -eq 1 || "$CI_ONLY" -eq 0 ) ]]; then
    "$LOCAL_SCRIPT" --preflight
  fi
}

if [[ "$PREFLIGHT_ONLY" -eq 1 ]]; then
  _preflight
  exit 0
fi

echo "== Reseed Chrome profile for $REPO =="
echo "Documentation: scripts/seed-chrome-profile.md"
echo

if [[ "$CI_ONLY" -eq 0 ]]; then
  _preflight
fi

if [[ "$CI_ONLY" -eq 0 ]]; then
  echo "== Step 1/4: Local Linux Chrome login (Docker + 2FA) =="
  "$LOCAL_SCRIPT"
else
  echo "== Step 1/4: Skipped local login (--ci-only) =="
  if ! gh release view chrome-profile-seed --repo "$REPO" >/dev/null 2>&1; then
    echo "Release chrome-profile-seed not found on $REPO. Run without --ci-only first." >&2
    exit 1
  fi
fi

if [[ "$LOCAL_ONLY" -eq 1 ]]; then
  echo
  echo "Local-only mode. Finish CI with:"
  echo "  ./scripts/reseed-chrome-profile.sh --ci-only"
  exit 0
fi

echo
echo "== Step 2/4: Seed Actions cache from release =="
gh workflow run seed-chrome-profile.yml --repo "$REPO"
_wait_for_workflow seed-chrome-profile.yml "Seed Chrome profile cache"

if [[ "$SKIP_FETCH" -eq 0 ]]; then
  echo
  echo "== Step 3/4: Verify CI fetch + publish calendar =="
  gh workflow run publish-calendar.yml --repo "$REPO"
  _wait_for_workflow publish-calendar.yml "Publish calendar"
else
  echo
  echo "== Step 3/4: Skipped publish-calendar.yml (--skip-fetch) =="
fi

if [[ "$SKIP_CLEANUP" -eq 0 ]]; then
  echo
  echo "== Step 4/4: Delete temporary release (security) =="
  if gh release view chrome-profile-seed --repo "$REPO" >/dev/null 2>&1; then
    gh release delete chrome-profile-seed --repo "$REPO" --yes
    echo "Deleted release chrome-profile-seed."
  else
    echo "Release chrome-profile-seed not found (already deleted)."
  fi
else
  echo
  echo "== Step 4/4: Skipped release cleanup (--skip-cleanup) =="
  echo "WARNING: chrome-profile-seed still contains a live Airbnb session." >&2
fi

echo
echo "Done."
echo "  • Profile is in Actions cache (restore key prefix: airbnb-chrome-profile-)"
echo "  • Refresh calendar anytime: gh workflow run publish-calendar.yml --repo $REPO"
