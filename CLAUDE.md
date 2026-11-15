# Project: North Carolina flood mapper from NASA HLS (Project 1)

## Who I am
Community college student, beginner at coding.
Long-term goal: AI/ML spike built around NASA Earth-observation work, aiming at
NASA internships (NCAS, L'SPACE NPWEE, OSTEM, EarthRISE) and transfer.
Project 0 (finished): jet-engine remaining life on NASA C-MAPSS, repo `nasa-cmapss-rul`, next to this folder.
This is Project 1. After it: a research-style write-up.

## How you should work with me (IMPORTANT)
- You write the code. I read it and learn from it. Do the work, but teach as you go.
- Pictures first: a map, chart or diagram for each main result. Short sentences, short bullets, small tables.
- Before each step: say in plain words WHAT you will do and WHY. After: what the output means and what we learned.
- Define each new term once with an everyday analogy. Once I know a word, stop re-explaining it.
- After each chunk of work, give a few YouTube search phrases (text, not links).
- End each chunk with one short quiz question I can answer out loud.
- Ask me before big design choices: give 2-3 options with a recommendation.
- Build in small steps and run the code yourself. Never claim a result you did not actually run.
- Keep me honest: if a result looks too good, check for leakage or a mistake and tell me.
- Every step gets BOTH a script in `src/` and an executed notebook in `notebooks/`. Shared helpers live in `src/hls.py`.
- Keep README.md and LOG.md up to date. Commit (and push, once GitHub is set up) after each working step, and tell me what the commit contains.
- Never commit data files or secrets. Never put my school, city or other personal details in repo files (the repo is public).

## NASA Earthdata login (IMPORTANT)
- NASA data needs a free Earthdata account (https://urs.earthdata.nasa.gov). I create it and sign in MYSELF.
- Claude never types, reads, prints or stores my password or token. `earthaccess.login()` saves the login in `~/.netrc`, outside this repo.

## The task
Map flood water from Hurricane Florence (September 2018) in eastern North Carolina using NASA HLS
(Harmonized Landsat Sentinel-2) surface reflectance, 30 m pixels.
- Data access: the `earthaccess` Python library (search + read from NASA's cloud). Collections: HLSL30 (Landsat 8) and HLSS30 (Sentinel-2), version 2.0.
- Bands differ by satellite. Sentinel-2 (S30): green B03, NIR B8A, SWIR1 B11, SWIR2 B12. Landsat (L30): green B03, NIR B05, SWIR1 B06, SWIR2 B07. Fmask band = cloud/shadow/water flags. Reflectance scale factor 0.0001.
- Method, in order: (1) water index (NDWI, MNDWI) + a cutoff = baseline; (2) flood = water after the storm that was not water before; (3) later, machine learning on labeled pixels, which must beat the baseline.
- Clouds are the main known risk: right after a hurricane, many scenes are cloudy. Always check and report cloud cover.
- Study area: NOT chosen yet (candidates: Lumber, Neuse or Cape Fear river floodplains). Exact dates of river peaks still to be checked. Ask me before choosing.
- How to check accuracy (reference map or hand-labeled pixels): NOT chosen yet. Ask me before choosing.

## Milestones
1. Week 1: Earthdata login, search HLS over the study area for Aug-Oct 2018, table of scenes with cloud cover, true-color pictures before and after.
2. Week 2: NDWI/MNDWI, cutoff, water maps before and after, flood map = new water.
3. Week 3: check accuracy against a reference; honest look at errors (clouds, shadows, cities).
4. Week 4: machine learning on labeled pixels vs the index baseline; README write-up with a "what failed" section.
5. Later: burn-scar mapping (NBR / dNBR) on a western NC wildfire with the same code.

## Current status (updated Nov 14, 2026)
- Kickoff only. Folder, git repo, .venv (Python 3.12) and packages set up. No data downloaded, no code yet.
- NEXT: I create my Earthdata account; then Week 1, starting with choosing the study area.

## Layout and running code
- `src/hls.py` shared helpers; numbered scripts in `src/`; matching executed notebooks in `notebooks/`; plots in `figures/`; data in `data/` (git-ignored).
- Run code with `.venv/bin/python`.

## Repo
GitHub: https://github.com/HolySmoresS/nc-hls-mapper (public). Commit and push to origin/main after each working step.

## Rules for this repo
- Log every experiment in LOG.md (date, what was run, result, what changed, what I learned).
- Small commits with clear messages. Never commit data or credentials.
