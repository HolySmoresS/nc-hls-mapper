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
- Method, in order: (1) water rule + a cutoff = baseline (textbook NDWI/MNDWI failed on this blackwater river; NIR-based rules are the baseline now); (2) flood = water after the storm that was not water before; (3) later, machine learning on labeled pixels, which must beat the baseline.
- Clouds are the main known risk: right after a hurricane, many scenes are cloudy. Always check and report cloud cover.
- Study area (chosen Nov 14, 2026): Lumber River at Lumberton, box (-79.15, 34.55, -78.90, 34.70), tile T17SPU. Key photos: Sentinel-2 Sept 18, 2018 (after, 86% clear); Landsat Aug 25 (100%) and Sentinel-2 Sept 6 (92%) as "before". Cape Fear (Fayetteville) Sept 18 was 79% clear: a possible second test area later.
- Clear share is always measured over the WHOLE box (a tile can cover only a sliver of it).
- How to check accuracy (reference map or hand-labeled pixels): NOT chosen yet. Ask me before choosing.

## Milestones
1. Week 1: Earthdata login, search HLS over the study area for Aug-Oct 2018, table of scenes with cloud cover, true-color pictures before and after.
2. Week 2: NDWI/MNDWI, cutoff, water maps before and after, flood map = new water.
3. Week 3: check accuracy against a reference; honest look at errors (clouds, shadows, cities).
4. Week 4: machine learning on labeled pixels vs the index baseline; README write-up with a "what failed" section.
5. Later: burn-scar mapping (NBR / dNBR) on a western NC wildfire with the same code.

## Current status (updated Nov 14, 2026)
- Set up: folder, git repo, .venv (Python 3.12), packages. Earthdata account made and login saved in ~/.netrc (done by me).
- Step 1 DONE: src/01_find_clear_photos.py + notebooks/01_find_clear_photos.ipynb counted clear photos per river; chose the Lumber River.
- Step 2 (Week 2) DONE: src/02_water_maps.py + notebooks/02_water_maps.ipynb. Before = Sentinel-2 Sept 6, after = Sentinel-2 Sept 18 (same satellite and tile). Textbook NDWI/MNDWI > 0 FAILED (blackwater river is darker in green than SWIR). Two NIR rules: dark-in-NIR (NIR < 0.10) = 11.3 km2 new flood; NIR-drop (after/before < 0.5) = 16.5 km2; overlap 63%. Area depends strongly on the cutoff.
- Week 3 plan (chosen Nov 14, 2026; done Nov 15): BOTH (a) our own answer key: ~300 random spots I label water / not water / can't tell on zoomed photos (main grade), and (b) an existing radar-based flood map as a second opinion, if one covers Lumberton near Sept 18. Check NOAA NGS airplane photos (Sept 15-22, 2018) for Lumberton coverage to help labeling.
- Findings (Nov 14, 2026):
  - NOAA NGS airplane photos DO cover Lumberton: Sept 19, 2018 covers the town and river corridor (one day after our Sept 18 HLS photo); Sept 20 covers the downstream (southeast) part. Sept 18 and Sept 17 flights do not cover it. Sharp enough to see flooded fields and roads; hard to judge under tree cover. Tiles (XYZ): https://stormscdn.ngs.noaa.gov/20180919{a,b,c}-rgb/{z}/{x}/{y} (also 20180920...). Viewer: https://storms.ngs.noaa.gov/storms/florence/
  - No ready-made radar flood map found for Lumberton. UAVSAR (airborne radar) flew the Lumber and Cape Fear rivers Sept 17-23, 2018 (Melancon et al. 2021, Remote Sensing 13:5098), but only raw radar images are public (ASF DAAC / JPL UAVSAR portal), so a radar map would have to be made by us. Copernicus EMS Sentinel-1 maps covered Jacksonville and Kinston, not Lumberton.
- Step 3 DONE (Nov 15, 2026; user chose to make our own radar map, Sentinel-1): src/radar.py (HyP3 RTC download, coverage check), src/noaa.py (NOAA tile helper), src/03_radar_flood_map.py + notebooks/03_radar_flood_map.ipynb. Sentinel-1A path 77, Sept 7 vs Sept 19 (path 150 only grazed the box). Radar open water VV < -17 dB finds only 0.9 km2 new water; overlap with NIR maps 2-3%. NOAA spot check (12 spots): NIR-only spots are mostly real shallow/vegetated flood; radar "brightened" spots are dry fields. NIR looks closer to the truth so far.
- HyP3/ASF needed a one-time Earthdata app approval (done by me).
- Step 4a DONE (Nov 15, 2026): src/04_make_label_sample.py picked 269 stratified spots (dark_nir 100, drop_only 50, radar_only 9, dry 110; seed 42) and saved NOAA photo chips to data/labels/ (git-ignored). src/04_label_server.py + src/label_page.html = blind, shuffled labeling page at http://localhost:8765; each click appends to data/labels/labels.csv (latest label per spot wins).
- Labels DONE (Nov 15, 2026): 269 spots first pass (about 2 s each), plus a blind second look at 40 random spots (`04_label_server.py --recheck`, saved to labels_recheck.csv). Both saved in results/04_labels.csv (no click times).
- Step 5 DONE: src/05_score_maps.py + notebooks/05_score_maps.ipynb. Weighted recall / precision: dark-in-NIR 44% / 48%, NIR-drop 56% / 42%, both NIR 43% / 49%, radar 1% / n.a. Overall accuracy 96% = same as "say dry everywhere" (misleading). Self-agreement 65% (90% without can't-tell). Real flood about 12 km2 in cloud-free box, uncertain.
- NEXT: undecided. Options to ask me about: Week 4 machine learning on labeled pixels (must beat the NIR baseline; labels are few, ~255), improve the rule (e.g. NIR + mask dark plowed fields), README write-up, or burn scars. Ask me before choosing.

## Layout and running code
- `src/hls.py` shared helpers; numbered scripts in `src/`; matching executed notebooks in `notebooks/`; plots in `figures/`; data in `data/` (git-ignored).
- Run code with `.venv/bin/python`.

## Repo
GitHub: https://github.com/HolySmoresS/nc-hls-mapper (public). Commit and push to origin/main after each working step.

## Rules for this repo
- Log every experiment in LOG.md (date, what was run, result, what changed, what I learned).
- Small commits with clear messages. Never commit data or credentials.
