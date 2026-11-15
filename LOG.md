# Experiment log
| Date | What I ran | Result | What I changed | What I learned |
|---|---|---|---|---|
| 2026-11-14 | (project kickoff) | - | Chose: Hurricane Florence 2018 flood, eastern NC; water index + cutoff first, machine learning later; data via `earthaccess`. Created repo, .venv (Python 3.12) and requirements.txt | HLS joins Landsat and Sentinel-2 into one matching set: 30 m pixels, a new picture every 2-3 days. Water reflects almost no near-infrared, so a water index can find it. Clouds after hurricanes are the main risk. |
