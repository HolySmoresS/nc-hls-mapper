# Project: North Carolina flood and burn-scar mapper from NASA HLS (Project 1)

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
5. Phase 2 (started Nov 15, 2026): burn-scar mapping (NBR / dNBR) on the Black Cove Complex, western NC, with the same code.

## Current status (updated Nov 15, 2026)
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
- Step 6 (Week 4 ML) DONE: src/features.py (21 clues, cached in data/06_features.npz) + src/06_machine_learning.py + notebooks/06_machine_learning.ipynb. By-area practice exams (4x4 blocks, 5 folds). Rule 44% / 48% recall/precision beats logistic regression 25% / 50% and random forest 23% / 59% (F1 0.46 vs 0.34). Random exams inflate precision (leak). ML did NOT beat the rule.
- Write-up DONE (Nov 15, 2026): README is the full story (summary, results, method, honesty checks, what failed, limits, next steps, credits). 05_score_maps.py falls back to results/04_labels.csv on a fresh clone.
- Project 1 version 1 COMPLETE.
- PHASE 2, BURN SCARS (started Nov 15, 2026). Choices I made: fire = Black Cove Complex if the photos allow (they do); answer key = official outline; scope = NBR rule + leaf-season check (compare with nearby unburned forest); machine learning only if the rule leaves room.
- Step 7 DONE (Nov 15, 2026): src/fires.py (FIRES, outline download to data/fires/, box = outline + 3 km) + src/07_find_fire_photos.py + notebooks/07_find_fire_photos.ipynb. Good photos before / after: Black Cove 13 / 6, Tellico 2 / 3, Great Lakes 10 / 6. Black Cove box (-82.391, 35.227, -82.188, 35.379), tile T17SLV, fire started Mar 19, 2025, grew until about Mar 31; outline 31.1 km2 from NIFC WFIGS (three pieces: Black Cove, Deep Woods, Fish Hook; "auto-generated", not certified; not in MTBS).
- Key Black Cove photos: before = Landsat Mar 18, 2025 (100%), Sentinel-2 Mar 11 (100%). During the fire = Mar 21, 23, 26 (lower-left lobe not burned yet on Mar 26). After it stopped = Sentinel-2 Apr 12 (80%) and Apr 20 (83%), then Jun 11 (96%, leaves out). An older burn sits at the bottom edge of the box in both photos (should not be flagged).
- Step 8 DONE (Nov 15, 2026; I chose to map both "after" photos and compare): src/08_burn_maps.py + notebooks/08_burn_maps.ipynb; hls.nbr, fires.outline_mask, fires.triangle_cutoff. April pair = Sentinel-2 Mar 11 vs Apr 12; March 26 pair = Landsat Mar 18 vs Mar 26. Flagged: April textbook (dNBR > 0.10) 4.4 km2, April histogram cutoff (+0.025) 7.7 km2; March 26 textbook 19.8 km2, histogram (+0.055) 26.9 km2; official outline 31.1 km2; the two histogram maps overlap 25%. Textbook cutoff FAILED on April: the whole box greened up (median dNBR -0.155). Cutoffs were fixed before comparing with the outline. dNBR and burn maps saved as data/08_*.tif.
- Step 9 DONE (Nov 15, 2026; I chose to try both fixes and compare): src/09_grade_burn_maps.py + notebooks/09_grade_burn_maps.ipynb; fires.ring_mask. Caught / right: April textbook 16% / 99%, April histogram 26% / 94%, April fix A (look-alike groups by NBR before, no outline) 42% / 26%, April fix B (ring 300 m - 2 km outside the outline) 37% / 32%; March 26 textbook 61% / 96%, March 26 histogram 73% / 84% (best, F1 0.78), fixes about 65% / 94%. Both fixes FAILED on April: false alarms along the mountain ridges, likely late green-up on high ground (NOT proven; no height data loaded). Timing beat method.
- Step 10 DONE (Nov 15, 2026; I chose to test the ridge guess): src/terrain.py (NASADEM download to data/dem/, height on the HLS grid, slope facing) + src/10_ridge_check.py + notebooks/10_ridge_check.ipynb. Guess HOLDS: fix A's false-alarm rate is 44% above 687 m vs 1-2% below 500 m; slope facing matters less (north 11%, others 21-26%). Fix C (look-alikes by score before AND height, 10 x 5 groups): April caught 52%, right 48%, F1 0.50 = best April map, still far behind March 26 histogram (73% / 84%, F1 0.78). Fix C is not a fresh exam (designed after seeing fix A's mistakes). Below about 430 m the height pattern reverses (unexplained).
- Step 11 DONE (Nov 15, 2026; I chose a second fire as a fresh exam): src/11_second_fire.py + notebooks/11_second_fire.ipynb. Great Lakes fire (Croatan NF, Apr 2023), answer key = NIFC certified final outline 130.1 km2 (fires.MORE_OUTLINES), Landsat pair Apr 18 -> May 4, Sentinel-2 pair Apr 10 -> May 10, recipe unchanged. Plain textbook cutoff: caught 83%, right 98% (F1 0.90). Fix C slightly WORSE than fix A (79% vs 85% caught): one look-alike group is 65% burned, so its median is no longer "unburned". Fixes add false alarms when there is little to fix. Bug fixed: triangle_cutoff now covers dNBR -2 to +2 (Black Cove numbers identical).
- Burn-phase conclusion so far: a plain before-minus-after map from two photos close in time is the best map on both fires; leaf-season corrections only pay off when the season really moved, and fix C does not generalize as "always better".
- Burn write-up DONE (Nov 15, 2026): README top sections cover both parts (goal, results, summary, results tables, honesty, what failed, limits); steps are "Part 1: floods" and "Part 2: burn scars". Summary chart: figures/11_both_fires.png.
- WRITE-UP CHOICES MADE (Nov 15, 2026): audience = NASA internship applications (reuse later for transfer); scope = Project 1 only (floods + burn scars), one line linking Project 0; format = short paper, about 6 pages (abstract, intro, data, methods, results, honesty checks, limits, references, 4-6 figures); location = `paper/` folder in this repo, Markdown. I want a separate research write-up for Project 0 (jet engines) LATER, in its own repo. Outline DONE: paper/outline.md. Outline decisions (Nov 15): working title "When the textbook method breaks: ..."; Figure 4 = figures/10_ridge_check.png; Figure 1 = locator map, DONE (Step 12: src/12_locator_map.py + notebooks/12_locator_map.ipynb, figures/12_locator_map.png; state outlines from Census TIGERweb in data/states/). Section 2 DRAFT 2 in paper/sections/02_study_areas_and_data.md (rewritten in plainer words after my first explain-back; second explain-back PASSED Nov 15; trim at the end). Section 3 (methods) DRAFT 1 in paper/sections/03_methods.md (explain-back NOT passed yet: on Nov 15 I asked for plain explanations of score/cutoff, 'normal', the four groups and exams by area instead; redo the explain-back before calling it final, and consider rewriting 3.3-3.5 more plainly first). Next: Section 4, then 5, 6, 1, 7, abstract last.
- (Original note) the research-style write-up for the whole project. Before writing anything, ask me these, with 2-3 options and a recommendation each:
  1. Who it is for and what it is for (NASA internship applications, transfer essays, a class, a poster?).
  2. Scope: Project 1 only (floods + burn scars), or Project 0 (jet engines, repo `../nasa-cmapss-rul`) as well.
  3. Format and length (short paper with abstract / methods / results / limits, a 2-page summary, a poster, slides).
  4. Where it lives (a `paper/` folder here, or its own repo).
  Source material: README.md (full story, all numbers checked against results/*.csv on Nov 15), LOG.md (every experiment, including failures), figures/ (figures/11_both_fires.png and figures/05_map_scores.png are the two summary charts). Do not invent or re-derive numbers; take them from results/*.csv. It is my write-up in my voice: draft in short plain sentences, and have me explain each section back before it is final.
- Other open ideas (not chosen): (b) make look-alike groups safe for large fires; (c) slope facing; (d) join early + late maps; (e) more fires; (f) back to flood ideas (more labels, Cape Fear). Ask me before choosing.

## Layout and running code
- `src/hls.py` shared helpers; numbered scripts in `src/`; matching executed notebooks in `notebooks/`; plots in `figures/`; data in `data/` (git-ignored).
- Run code with `.venv/bin/python`.

## Repo
GitHub: https://github.com/HolySmoresS/nc-hls-mapper (public). Commit and push to origin/main after each working step.

## Rules for this repo
- Log every experiment in LOG.md (date, what was run, result, what changed, what I learned).
- Small commits with clear messages. Never commit data or credentials.
