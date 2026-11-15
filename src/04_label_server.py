"""Step 4b: a tiny local web page for labeling spots (water / not water / can't tell).

Run:  .venv/bin/python src/04_label_server.py   then open http://localhost:8765
- Runs only on this Mac (localhost). Nothing is published.
- Every click is saved at once to data/labels/labels.csv, so you can stop and come back.
- Spots are shown in a shuffled order, and the page never says which map picked a spot,
  so the labels can't be nudged by knowing what a map "expects" (a blind test).
"""
import argparse
import csv
import json
import random
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS_DIR = ROOT / "data" / "labels"
PAGE = Path(__file__).with_name("label_page.html")
PORT = 8765
ALLOWED = {"water", "not_water", "cant_tell"}
RECHECK_N = 40
lock = threading.Lock()
RECHECK = False  # set by --recheck: a "second look" at 40 random spots, saved to a separate file


def spot_ids():
    with open(LABELS_DIR / "sample.csv") as f:
        ids = [row["id"] for row in csv.DictReader(f)]
    random.Random(7).shuffle(ids)  # fixed shuffle: same order every time, groups mixed together
    if RECHECK:
        ids = random.Random(11).sample(ids, RECHECK_N)  # different random 40, different order
    return ids


def labels_csv():
    """First pass -> labels.csv. Second look -> labels_recheck.csv (never overwrites the first pass)."""
    return LABELS_DIR / ("labels_recheck.csv" if RECHECK else "labels.csv")


def read_labels():
    """Latest label for each spot (a later click on the same spot replaces an earlier one)."""
    LABELS_CSV = labels_csv()
    if not LABELS_CSV.exists():
        return {}
    with open(LABELS_CSV) as f:
        return {row["id"]: row["label"] for row in csv.DictReader(f)}


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep the terminal quiet
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = PAGE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/spots":
            self.send_json({"order": spot_ids(), "labels": read_labels(), "mode": "recheck" if RECHECK else "first"})
        elif self.path.startswith("/chips/") and self.path.endswith(".jpg") and "/.." not in self.path:
            f = LABELS_DIR / "chips" / Path(self.path).name
            if not f.exists():
                return self.send_error(404)
            body = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/label":
            return self.send_error(404)
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if data.get("label") not in ALLOWED or data.get("id") not in set(spot_ids()):
            return self.send_json({"ok": False}, 400)
        with lock:
            LABELS_CSV = labels_csv()
            new = not LABELS_CSV.exists()
            with open(LABELS_CSV, "a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["id", "label", "time_utc"])
                w.writerow([data["id"], data["label"], datetime.now(timezone.utc).isoformat(timespec="seconds")])
        self.send_json({"ok": True})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--recheck", action="store_true", help="second look at 40 random spots, saved separately")
    RECHECK = ap.parse_args().recheck
    print(f"Labeling page ({'second look, 40 spots' if RECHECK else 'all spots'}): http://localhost:{PORT}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
