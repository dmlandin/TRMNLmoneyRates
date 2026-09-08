#!/usr/bin/env bash
#
# Hourly TRMNL money-rates updater for a local (Unraid) Docker host.
# Replaces the GitHub Action: clones/refreshes the repo, runs generate_html.py,
# then commits & pushes the regenerated files back to GitHub.
#
set -euo pipefail

# --- Required configuration -------------------------------------------------
: "${FRED_API_KEY:?FRED_API_KEY must be set}"
: "${GITHUB_TOKEN:?GITHUB_TOKEN must be set (fine-grained PAT, Contents: read/write)}"

# --- Optional configuration (sensible defaults) -----------------------------
REPO_URL="${REPO_URL:-https://github.com/dmlandin/TRMNLmoneyRates.git}"
BRANCH="${BRANCH:-main}"
GIT_NAME="${GIT_AUTHOR_NAME:-trmnl-rates-bot}"
GIT_EMAIL="${GIT_AUTHOR_EMAIL:-trmnl-rates-bot@users.noreply.github.com}"
RUN_ON_START="${RUN_ON_START:-true}"
WORKDIR="/data/repo"
# Optional: mount a host directory here to keep logs across container restarts.
LOG_DIR="${LOG_DIR:-}"
# How many days of per-day logfiles to keep (older ones are pruned each run).
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-2}"

# Path of today's logfile (one file per UTC day, so retention is age-based).
logfile() { echo "$LOG_DIR/updater-$(date -u +%F).log"; }

# Emit a timestamped line to the console and, if LOG_DIR is set, today's file.
log() {
  local line="[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"
  echo "$line"
  [ -n "$LOG_DIR" ] && echo "$line" >> "$(logfile)"
}

# Delete per-day logfiles older than the retention window. -mtime +N matches
# files last modified more than N*24h ago, so +(DAYS-1) keeps the last DAYS.
prune_logs() {
  [ -n "$LOG_DIR" ] || return 0
  find "$LOG_DIR" -maxdepth 1 -name 'updater-*.log' \
    -mtime "+$((LOG_RETENTION_DAYS - 1))" -delete 2>/dev/null || true
}

if [ -n "$LOG_DIR" ]; then
  mkdir -p "$LOG_DIR"
  log "Persisting logs to $LOG_DIR/updater-<date>.log (keeping ${LOG_RETENTION_DAYS} days)"
fi

# --- One-time git setup -----------------------------------------------------
git config --global user.name "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"
git config --global credential.helper store
git config --global --add safe.directory "$WORKDIR"

# Store the token so HTTPS pushes to github.com authenticate non-interactively.
# Lives only inside the container's /root, never echoed to logs.
printf 'https://x-access-token:%s@github.com\n' "$GITHUB_TOKEN" > "$HOME/.git-credentials"
chmod 600 "$HOME/.git-credentials"

# --- Helpers ----------------------------------------------------------------
refresh_repo() {
  if [ ! -d "$WORKDIR/.git" ]; then
    log "Cloning $REPO_URL (branch $BRANCH) ..."
    git clone --branch "$BRANCH" "$REPO_URL" "$WORKDIR"
  fi
  # Discard any local state and match the remote before regenerating.
  git -C "$WORKDIR" fetch --quiet origin "$BRANCH"
  git -C "$WORKDIR" reset --hard --quiet "origin/$BRANCH"
}

run_job() {
  log "Starting rate update."
  prune_logs
  refresh_repo
  # Capture the generator's own stdout/stderr (incl. tracebacks) to today's
  # logfile when LOG_DIR is set, while still showing it in `docker logs`.
  if [ -n "$LOG_DIR" ]; then
    ( cd "$WORKDIR" && FRED_API_KEY="$FRED_API_KEY" python generate_html.py ) 2>&1 | tee -a "$(logfile)"
  else
    ( cd "$WORKDIR" && FRED_API_KEY="$FRED_API_KEY" python generate_html.py )
  fi

  cd "$WORKDIR"
  git add rates.html trmnl_layout.json
  if git diff --cached --quiet; then
    log "No changes to commit."
    return 0
  fi

  git commit --quiet -m "Update rates [ci skip]"
  # Rebase on top of anything pushed since the reset (e.g. a quarterly
  # medical_spreads update) so the push is a clean fast-forward.
  git pull --rebase --quiet origin "$BRANCH"
  git push --quiet origin "$BRANCH"
  log "Pushed updated rates."
}

# Seconds until the next top of the hour, to mimic cron "0 * * * *".
seconds_until_next_hour() {
  local min sec
  min=$(date -u +%M)
  sec=$(date -u +%S)
  echo $(( ((59 - 10#$min) * 60) + (60 - 10#$sec) ))
}

# --- Main loop --------------------------------------------------------------
if [ "$RUN_ON_START" = "true" ]; then
  run_job || log "Job failed; will retry next cycle."
fi

while true; do
  wait_secs=$(seconds_until_next_hour)
  log "Sleeping ${wait_secs}s until the next top of the hour."
  sleep "$wait_secs"
  run_job || log "Job failed; will retry next cycle."
done
