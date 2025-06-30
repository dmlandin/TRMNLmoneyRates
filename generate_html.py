import requests
import os
from datetime import datetime

API_KEY = os.environ["FRED_API_KEY"]
SERIES = {
    "Fed Funds Rate": "FEDFUNDS",
    "SOFR": "SOFR",
    "10-Year Treasury": "GS10",
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
timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

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
