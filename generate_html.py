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

# Get all values
values = {label: fetch_latest(code) for label, code in SERIES.items()}
timestamp = datetime.now(ZoneInfo("America/Phoenix")).strftime("%Y-%m-%d %H:%M:%S UTC")

# Build HTML
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
  </body>
</html>"""

with open("rates.html", "w") as f:
    f.write(html)


# also going to serve a json file
json_data = {
    "fedFundsRate": values["Fed Funds Rate"],
    "sofr": values["SOFR"],
    "tenYearTreasury": values["10-Year Treasury"],
    "primeRate": values["Prime Rate"],
    "lastUpdated": timestamp
}

with open("rates.json", "w") as f:
    json.dump(json_data, f, indent=2)

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
        ]
    }
}

with open("trmnl_layout.json", "w") as f:
    json.dump(layout_json, f, indent=2)
