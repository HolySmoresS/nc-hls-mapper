# Paper outline (draft 1)

**For:** NASA internship applications (NCAS, L'SPACE NPWEE, OSTEM, EarthRISE).
**Covers:** Project 1 only (floods + burn scars). Project 0 gets one line in "About this work".
**Length:** about 6 pages, 5 figures, 2 tables.
**Rule:** every number comes from `results/*.csv` (file named next to it). No new analysis in the paper.

## Working title
> When the textbook method breaks: honest flood and burn-scar maps of North Carolina from NASA HLS

Other options: "Simple rules, honest grades: ..." or "Mapping floods and burn scars with NASA HLS, and checking the maps fairly".

## The one question the paper answers
Do textbook satellite methods work on unusual places (a tea-colored river, a mountain spring), and does a simple rule with an honest grade beat fancier methods?

## Sections

| # | Section | Pages | Main point |
|---|---|---|---|
| 0 | Abstract | 0.25 | Question, data, method, 3 key numbers, main lesson |
| 1 | Introduction | 0.5 | Why fast disaster maps matter; why grading them is hard |
| 2 | Study areas and data | 0.75 | Three places, HLS + helpers, how photos were chosen |
| 3 | Methods | 1.25 | Flood rule, burn score, cutoffs, answer keys, fair tests |
| 4 | Results: floods | 1 | Textbook fails; NIR rule ~half caught, ~half right; ML loses |
| 5 | Results: burn scars | 1 | Timing beats method; fix C fails the fresh exam |
| 6 | Discussion and limits | 0.75 | The common thread; what failed; what we can't claim |
| 7 | Conclusion and next steps | 0.25 | Three sentences + 3 next steps |
| - | References, data credits, code link | 0.25 | |

### 0. Abstract (write it LAST)
About 150 words. Must contain:
- Floods: dark-in-NIR rule caught 44%, right 48% (`05_map_scores.csv`); beat MNDWI, radar, 2 ML models.
- Burns: plain map caught 73% / right 84% at Black Cove, 83% / 98% at Great Lakes (`11_both_fires.csv`).
- Lesson: textbook method broke where the place was unusual; fixes had to pass a fresh exam.

### 1. Introduction
- Disaster maps from satellites are needed fast; clouds and odd places get in the way.
- Gap: many maps are reported with "overall accuracy", which can look great while finding nothing.
- What I did, in 3 bullets: floods (Florence 2018, Lumberton), burns (two NC fires), honest grading.
- Contributions: (1) a hand-made blind answer key, (2) a fresh-exam test of a fix, (3) a list of what failed.

### 2. Study areas and data
- **Figure 1 (NEW, to make):** NC locator map with the 3 boxes (Lumberton, Black Cove, Great Lakes).
- HLS v2.0 (HLSL30, HLSS30), 30 m. Fmask for clouds.
- Helpers: NOAA airplane photos (flood answer key), Sentinel-1 radar via HyP3, NIFC fire outlines, NASADEM height.
- Photo choice: clear share over the whole box (`01_summary.csv`: Lumber 4 days after landfall vs 17 and 19).
- Small table: each place, before/after photo dates, clear share.

### 3. Methods
- 3.1 Flood = water after, not water before. Water rules: NDWI/MNDWI (textbook), NIR < 0.10, NIR fell by half.
- 3.2 Burn = NBR before minus NBR after (dNBR). Cutoffs: textbook 0.10, histogram (triangle method).
- 3.3 Leaf-season fixes A, B, C in one short table (what "normal" means for each).
- 3.4 Answer keys: 269 blind stratified spots on NOAA photos (floods); official outlines (burns).
- 3.5 Fair grading: recall/precision/F1, weights, bootstrap ranges, tests by area for ML, fresh exam on a second fire, cutoffs fixed before grading.

### 4. Results: floods
- **Figure 2:** `figures/02_flood_maps_compared.png` (textbook vs NIR maps).
- **Figure 3:** `figures/05_map_scores.png` (caught vs right for every map).
- **Table 1:** map scores from `05_map_scores.csv` + `06_scores_by_area.csv` (rule F1 0.46 vs ML 0.34).
- Points: MNDWI found almost nothing; radar caught 1%; "say dry" also scores 96% accuracy; wide ranges (26-82%).
- Labeler check: same answer 65%, 90% without can't-tell (`05_self_agreement.csv`).

### 5. Results: burn scars
- **Figure 4:** `figures/10_ridge_check.png` (tells the "why" story).
- **Figure 5:** `figures/11_both_fires.png` (F1 of all maps, both fires).
- **Table 2:** the 8 rows from the README burn table (`11_both_fires.csv`).
- Points: a month apart, textbook caught 16%; 8 days apart, 73%; height explains ridge false alarms; fix C best only where it was built, worse on Great Lakes (79% vs 85% caught).

### 6. Discussion and limits
- Thread: unusual place breaks the textbook; simple + honest beats fancy; fixes must pass unseen data.
- What failed (short list, from README).
- Limits: one flood, two fires, one labeler, clouds (22% of flood box), water under trees, outlines are not perfect truth.

### 7. Conclusion and next steps
- More labels; Cape Fear; longer-wave radar (UAVSAR) for water under trees.

### About this work (short box at the end)
- Student project, code and figures at the repo link. Earlier project: jet-engine remaining life (C-MAPSS).

## References to check before citing (do NOT cite until checked)
- HLS: Claverie et al., 2018, Remote Sensing of Environment.
- NDWI: McFeeters, 1996. MNDWI: Xu, 2006.
- NBR / dNBR: Key and Benson, 2006 (FIREMON).
- Triangle threshold: Zack et al., 1977.
- UAVSAR on Florence: Melancon et al., 2021, Remote Sensing 13:5098.
- Data credits: same list as the README "Data and credits" section.

## Decisions (Nov 15, 2026)
1. Title: the working title, "When the textbook method breaks: ...".
2. Figure 4: the ridge check, `figures/10_ridge_check.png`.
3. Figure 1: YES, make the new locator map (`src/12_locator_map.py` + notebook, no new analysis).
