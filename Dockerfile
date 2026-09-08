FROM python:3.11-slim

# git: clone/commit/push back to GitHub
# tzdata: generate_html.py uses ZoneInfo("America/Phoenix")
# ca-certificates: HTTPS to FRED + GitHub
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Persistent checkout + git credentials live here (mount as an Unraid volume)
VOLUME ["/data"]
ENV RUN_ON_START=true

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
