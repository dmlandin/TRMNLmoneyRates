import os
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from zoneinfo import ZoneInfo

API_KEY = os.environ["FRED_API_KEY"]

# Daily series only. FEDFUNDS and MPRIME are monthly averages published in the
# first week of the following month and were showing values up to ~7 weeks
# stale; DFF and DPRIME are their daily equivalents. Keys are display labels
# that appear in trmnl_layout.json rows -- the TRMNL markup depends on them.
SERIES = {
    "Fed Funds Rate": "DFF",
    "SOFR": "SOFR",
    "10-Year Treasury": "DGS10",
    "Prime Rate": "DPRIME",
    "30-Year Treasury": "DGS30"
}

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
# (connect, read) seconds. An untimed request can hang the whole job.
TIMEOUT = (10, 30)

# One session for all requests, with automatic retry/backoff on transient
# failures (429/5xx, connection errors, read timeouts). Sleeps between
# attempts are 0s, 4s, 8s, 16s, 32s (urllib3 formula: factor * 2**(n-1));
# FRED's Retry-After header is honoured when present.
_retry = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["GET"]),
    respect_retry_after_header=True,
)
SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(max_retries=_retry))
SESSION.headers["User-Agent"] = (
    "TRMNLmoneyRates/1.0 (+https://github.com/dmlandin/TRMNLmoneyRates)"
)


def fetch_latest(series_id):
    """Return (value, observation_date) for the most recent real observation.

    FRED emits "." for dates with no observation (weekends, market holidays),
    and the business-day series (DGS10, DPRIME, SOFR) frequently have "." as
    their newest row, so pull the last 10 and take the first non-missing one.

    Any failure -- HTTP error after retries, malformed body, or ten missing
    values in a row -- raises so the script exits non-zero and leaves the
    previously published JSON untouched. Stale-but-known beats silently wrong.
    """
    params = {
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 10,
    }
    resp = SESSION.get(FRED_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    observations = resp.json()["observations"]
    for obs in observations:
        if obs["value"] != ".":
            return float(obs["value"]), obs["date"]
    raise RuntimeError(
        f"FRED series {series_id}: no non-missing value in the latest "
        f"{len(observations)} observations"
    )


# Fetch rates. Fail closed: if any series fails, the exception propagates and
# nothing is written.
values = {}
as_of = {}
for label, code in SERIES.items():
    values[label], as_of[label] = fetch_latest(code)
timestamp = datetime.now(ZoneInfo("America/Phoenix")).strftime("%Y-%m-%d %H:%M:%S MST")

# Load medical spreads
SPREADS_FILE = "medical_spreads.json"
with open(SPREADS_FILE) as f:
    spreads = json.load(f)["layout"]["rows"]

# The positional split below (first 4 = Fixed, next 4 = Floating, each ending
# in a QoQ row) is only valid for the shape extract_medical_spreads.py emits
# today. If Chatham changes the PDF layout the extractor may emit something
# else, and silently mis-mapping spreads would produce plausible-looking but
# wrong loan pricing. Refuse to proceed rather than guess.
_titles = [row.get("title") for row in spreads]
if len(spreads) != 8 or _titles[3] != "QoQ" or _titles[7] != "QoQ":
    raise RuntimeError(
        f"{SPREADS_FILE}: expected exactly 8 rows with title 'QoQ' at index 3 "
        f"and 7 (Fixed: Low Risk, Core, High Risk, QoQ; then Floating: same), "
        f"but found {len(spreads)} rows with titles {_titles}"
    )

# Assume first 4 = Fixed, next 4 = Floating
fixed_rates = []
floating_rates = []

for i, row in enumerate(spreads):
    title = row["title"]
    value = row["value"].replace("%", "").strip()

    try:
        spread_val = float(value)
    except ValueError:
        continue

    if i < 4 and title != "QoQ":
        combined = round(values["10-Year Treasury"] + spread_val, 2)
        fixed_rates.append({"title": title, "value": f"{combined}%"})

    elif i >= 4 and title != "QoQ":
        combined = round(values["SOFR"] + spread_val, 2)
        floating_rates.append({"title": title, "value": f"{combined}%"})

# Write HTML
def rate_line(label):
    return (f"    <p><strong>{label}:</strong> {values[label]}% "
            f"<small>(as of {as_of[label]})</small></p>\n")

html = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Money Rates</title>
  </head>
  <body>
    <h2>📈 Money Rates</h2>
    <p><em>Last updated: {timestamp}</em></p>
"""
for label in ["Fed Funds Rate", "SOFR", "10-Year Treasury", "30-Year Treasury", "Prime Rate"]:
    html += rate_line(label)

html += """
    <h3>💡 Fixed Rates (10Y + Spread)</h3>
    <ul>
"""

for r in fixed_rates:
    html += f"      <li><strong>{r['title']}:</strong> {r['value']}</li>\n"

html += """    </ul>
    <h3>💡 Floating Rates (SOFR + Spread)</h3>
    <ul>
"""

for r in floating_rates:
    html += f"      <li><strong>{r['title']}:</strong> {r['value']}</li>\n"

html += """    </ul>
  </body>
</html>"""

with open("rates.html", "w", encoding="utf-8") as f:
    f.write(html)

# Write JSON. The TRMNL markup editor is configured by hand against this
# structure: do not rename, remove, reorder, or restructure existing keys.
# New keys may be appended (unused keys are ignored by the template).
layout_json = {
    "layout": {
        "type": "list",
        "title": "Money Rates",
        "rows": [
            {"title": "Fed Funds Rate", "value": f"{values['Fed Funds Rate']}%"},
            {"title": "SOFR", "value": f"{values['SOFR']}%"},
            {"title": "10-Year Treasury", "value": f"{values['10-Year Treasury']}%"},
            {"title": "Prime Rate", "value": f"{values['Prime Rate']}%"},
            {"title": "30-Year Treasury", "value": f"{values['30-Year Treasury']}%"},
            {"title": "Updated", "value": timestamp}
        ],
        "fixedRates": fixed_rates,
        "floatingRates": floating_rates,
        # Observation date of each rate, so the display can show data vintage
        # (daily series lag: a Monday-morning run sees Friday's DGS10).
        "asOf": as_of
    }
}

with open("trmnl_layout.json", "w") as f:
    json.dump(layout_json, f, indent=2)
