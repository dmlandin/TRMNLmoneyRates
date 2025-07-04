import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_DIR = Path("market spreads report")

class updateSpreadsHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".pdf"):
            pdf_path = Path(event.src_path)
            print(f"📥 New PDF detected: {pdf_path.name}")

            # Run the parsing script
            subprocess.run(["python", "extract_medical_spreads.py", str(pdf_path)], check=True)

            # Derive expected output filename (based on parsed PDF title)
            # Use last modified .json file instead (safe)
            json_files = sorted(Path(".").glob("*_Chatham_Financial_Medical_Spreads.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if json_files:
                output_json = json_files[0]
                print(f"📤 Committing {output_json.name} to GitHub...")
                subprocess.run(["git", "add", str(output_json)], check=True)
                subprocess.run(["git", "commit", "-m", f"Add medical spreads: {output_json.name}"], check=True)
                subprocess.run(["git", "push"], check=True)
            else:
                print("❌ No output JSON found to commit.")

if __name__ == "__main__":
    print(f"👀 Watching folder: {WATCH_DIR.resolve()}")
    event_handler = updateSpreadsHandler()
    observer = Observer()
    observer.schedule(event_handler, str(WATCH_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()