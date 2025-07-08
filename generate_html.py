import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

API_KEY = os.environ["FRED_API_KEY"]
SERIES = {
    "Fed Funds Rate": "FEDFUNDS",
    "SOFR": "SOFR",
    "10-Year Treasury": "DGS10",
    "Prime Rate": "MPRIME"
}

def fetch_latest(series_id):
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    return data['observations'][0]['value']

# Fetch rates
values = {label: float(fetch_latest(code)) for label, code in SERIES.items()}
timestamp = datetime.now(ZoneInfo("America/Phoenix")).strftime("%Y-%m-%d %H:%M:%S MST")

# Load medical spreads
with open("medical_spreads.json") as f:
    spreads = json.load(f)["layout"]["rows"]

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
html = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Money Rates</title>
  </head>
  <body>
    <h2>📈 Money Rates</h2>
    <p><em>Last updated: {timestamp}</em></p>
    <p><strong>Fed Funds Rate:</strong> {values['Fed Funds Rate']}%</p>
    <p><strong>SOFR:</strong> {values['SOFR']}%</p>
    <p><strong>10-Year Treasury:</strong> {values['10-Year Treasury']}%</p>
    <p><strong>Prime Rate:</strong> {values['Prime Rate']}%</p>

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

# Write JSON
layout_json = {
    "layout": {
        "type": "list",
        "title": "Money Rates",
        "rows": [
            {"title": "Fed Funds Rate", "value": f"{values['Fed Funds Rate']}%"},
            {"title": "SOFR", "value": f"{values['SOFR']}%"},
            {"title": "10-Year Treasury", "value": f"{values['10-Year Treasury']}%"},
            {"title": "Prime Rate", "value": f"{values['Prime Rate']}%"},
            {"title": "Updated", "value": timestamp}
        ],
        "fixedRates": fixed_rates,
        "floatingRates": floating_rates
    }
}

with open("trmnl_layout.json", "w") as f:
    json.dump(layout_json, f, indent=2)

