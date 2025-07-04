import pdfplumber
import json
import re
import sys
from pathlib import Path

def extract_medical_spreads(pdf_file: str):
    labels = ["Low Risk", "Core", "High Risk", "QoQ"]
    layout = {
        "layout": {
            "type": "grid",
            "title": "",
            "rows": []
        }
    }

    quarter_year = "Unknown"

    def extract_spreads(line):
        return re.findall(r"[-+]?\d+\.\d+%", line)

    with pdfplumber.open(pdf_file) as pdf:
        # Search for "Q1 2025" style in first page
        first_page_text = pdf.pages[0].extract_text()
        match = re.search(r"(Q[1-4])\s+(\d{4})", first_page_text)
        if match:
            quarter_year = f"{match.group(2)}{match.group(1)}"
            layout["layout"]["title"] = f"Medical CRE Spreads – {match.group(1)} {match.group(2)}"
        else:
            layout["layout"]["title"] = "Medical CRE Spreads"

        for page_number in [1, 2]:  # 0-indexed pages 2 & 3
            page = pdf.pages[page_number]
            text = page.extract_text()

            for line in text.splitlines():
                if "Medical" in line:
                    spreads = extract_spreads(line)
                    if len(spreads) >= 4:
                        prefix = "Fixed" if page_number == 1 else "Floating"
                        for i, label in enumerate(labels):
                            layout["layout"]["rows"].append({
                                "title": f"{prefix} {label}",
                                "value": spreads[i]
                            })
                    break
#save file and to overwrite existing 
    output_file = Path("medical_spreads.json")
    with output_file.open("w") as f:
        json.dump(layout, f, indent=2)
    print(f"✅ Saved: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_medical_spreads.py <pdf_path>")
        sys.exit(1)

    pdf_input = sys.argv[1]
    extract_medical_spreads(pdf_input)