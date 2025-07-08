import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
import pdfplumber

def sanitize(text):
    return re.sub(r'\s+', ' ', text.strip().lower())

def extract_medical_spreads_from_page(lines, label):
    for line in lines:
        if sanitize(line).startswith("medical"):
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 5:
                return {
                    f"{label} Low Risk": parts[1],
                    f"{label} Core": parts[2],
                    f"{label} High Risk": parts[3],
                    f"{label} QoQ": parts[4]
                }
    return {}

def get_quarter_and_year(text):
    match = re.search(r'Q[1-4]\s+\d{4}', text)
    return match.group(0) if match else "Unknown"

def find_latest_pdf(folder_path):
    pdfs = list(Path(folder_path).glob("*.pdf"))
    if not pdfs:
        return None
    latest_file = max(pdfs, key=lambda f: f.stat().st_ctime)
    return str(latest_file)

def extract_and_write_json(latest_pdf):
    floating_data = {}
    fixed_data = {}
    quarter = "Unknown"

    with pdfplumber.open(latest_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.splitlines()
            if quarter == "Unknown":
                quarter = get_quarter_and_year(text)

            if "Floating-rate spreads" in text:
                floating_data = extract_medical_spreads_from_page(lines, "Floating")

            if "Fixed-rate spreads" in text:
                fixed_data = extract_medical_spreads_from_page(lines, "Fixed")

    layout = {
        "type": "grid",
        "title": f"Medical CRE Spreads – {quarter}",
        "rows": []
    }

    for label, value in {**fixed_data, **floating_data}.items():
        layout["rows"].append({"title": label, "value": value})

    output_path = "medical_spreads.json"
    with open(output_path, "w") as f:
        json.dump({"layout": layout}, f, indent=2)

    print(f"✅ Extracted spreads and saved: {output_path}")
    return output_path

def commit_to_git(file_path):
    subprocess.run(["git", "add", file_path], check=True)
    subprocess.run(["git", "commit", "-m", "Update medical spreads [ci skip]"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("✅ Git commit and push completed.")

def main():
    folder = "market spreads report"
    latest_pdf = find_latest_pdf(folder)
    if not latest_pdf:
        print("❌ No PDF found in folder.")
        return

    print(f"📄 Using latest PDF: {latest_pdf}")
    output_file = extract_and_write_json(latest_pdf)
    commit_to_git(output_file)

if __name__ == "__main__":
    main()
