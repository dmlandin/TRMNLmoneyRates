# Deploying the hourly rates updater on Unraid (Docker)

This replaces the old GitHub Action. A small Docker container runs on your
Unraid server, fetches FRED rates **every hour**, regenerates `rates.html` and
`trmnl_layout.json`, and pushes them back to this GitHub repo.

## How it works

On each cycle the container:

1. Clones the repo into a persistent `/data` volume (or `git reset --hard` to
   the latest `main` if already cloned), so it always runs the newest committed
   `generate_html.py`.
2. Runs `python generate_html.py` with your `FRED_API_KEY`.
3. Commits and pushes `rates.html` + `trmnl_layout.json` if they changed.
4. Sleeps until the top of the next hour and repeats.

`restart: unless-stopped` keeps it running across reboots. The quarterly
`extract_medical_spreads.py` (the Chatham PDF parser) is **not** part of this
container — keep running that manually when a new PDF arrives.

## One-time prerequisites

1. **FRED API key** — https://fredaccount.stlouisfed.org/apikeys
2. **GitHub token** — create a **fine-grained Personal Access Token** at
   https://github.com/settings/personal-access-tokens
   - Repository access: only `dmlandin/TRMNLmoneyRates`
   - Permissions → **Contents: Read and write**
   - Copy the token (starts with `github_pat_...`).

## Option A — Unraid "Add Container" (recommended)

Unraid can't build a Dockerfile from the GUI, so build the image once over SSH,
then point a container at it.

**1. Build the image on the Unraid box (SSH):**

```sh
cd /mnt/user/appdata
git clone https://github.com/dmlandin/TRMNLmoneyRates.git trmnl-rates-src
cd trmnl-rates-src
docker build -t trmnl-money-rates:latest .
```

(When `generate_html.py` or this Docker setup changes, `git pull` here and
`docker build` again. The *running* container always pulls the latest repo at
runtime, so a rebuild is only needed if the entrypoint/Dockerfile itself
changes.)

**2. Docker → Add Container** with:

| Field | Value |
|-------|-------|
| Name | `trmnl-money-rates` |
| Repository | `trmnl-money-rates:latest` |
| Network Type | `bridge` |
| Variable: `FRED_API_KEY` | *(your FRED key)* |
| Variable: `GITHUB_TOKEN` | *(your fine-grained PAT)* |
| Variable: `REPO_URL` | `https://github.com/dmlandin/TRMNLmoneyRates.git` |
| Variable: `BRANCH` | `main` |
| Path: `/data` | `/mnt/user/appdata/trmnl-money-rates` |

Set the two secret variables to **masked** if you like. Apply — it starts
immediately (runs once on start, then hourly).

## Option B — docker-compose (CLI)

```sh
cd /mnt/user/appdata/trmnl-rates-src
cp .env.example .env      # then edit .env with your FRED_API_KEY + GITHUB_TOKEN
docker compose up -d --build
```

## Verifying

```sh
docker logs -f trmnl-money-rates
```

You should see `Starting rate update.` then `Pushed updated rates.` (or
`No changes to commit.`). Confirm a new commit appears on GitHub from
`trmnl-rates-bot`.

## Configuration reference

| Env var | Required | Default | Purpose |
|---------|----------|---------|---------|
| `FRED_API_KEY` | yes | — | St. Louis FRED API key |
| `GITHUB_TOKEN` | yes | — | Fine-grained PAT, Contents: read/write |
| `REPO_URL` | no | this repo | Repo to update |
| `BRANCH` | no | `main` | Branch to push to |
| `RUN_ON_START` | no | `true` | Run once immediately on container start |
| `GIT_AUTHOR_NAME` | no | `trmnl-rates-bot` | Commit author name |
| `GIT_AUTHOR_EMAIL` | no | `trmnl-rates-bot@users.noreply.github.com` | Commit author email |

## Rolling back to GitHub Actions

The workflow at `.github/workflows/update-rates.yml` is kept as a manual
fallback. Stop the container and uncomment the `schedule:` block in that file to
return to hourly runs on GitHub.
