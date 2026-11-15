<!-- DRAFT 1 (Nov 15, 2026). Not final until I can explain it back. Every number has its source in a comment. Budget: 1.25 pages. -->

## 3. Methods

Every map in this paper is made the same way: turn each pixel's light into a score, then pick a **cutoff**. Pixels on one side of the cutoff are flagged. The method has three parts: the score, the cutoff, and the grade.

### 3.1 Flood maps
**Flood = water after the storm that was not water before.** I made a water map for each photo, then kept only the new water.

I tried three water rules:
- **Textbook indexes (NDWI, MNDWI).** They compare green light with near-infrared or shortwave infrared, and call a pixel water when the index is above 0.
- **Dark in near-infrared.** Water swallows NIR, so water = NIR below 0.10.
- **NIR fell by half.** Flood = NIR after is less than half of NIR before.

I picked the 0.10 cutoff from the histogram of the whole box, before looking at any answer key. Pixels with cloud or cloud shadow on either day were left out.

<!-- rules and cutoffs: src/02_water_maps.py (NIR_DARK = 0.10, ratio < 0.5) -->

### 3.2 Burn maps
Living leaves reflect a lot of NIR and little shortwave infrared. Burned ground does the opposite. The **Normalized Burn Ratio (NBR)** compares the two. The burn score is **dNBR = NBR before minus NBR after**: a big drop means burned.

I used two cutoffs, both chosen without the fire outline:
- **Textbook:** dNBR above 0.10.
- **Histogram (the triangle method):** most of the box did not burn, so its histogram is one big pile with a tail. The cutoff is the foot of the pile.

<!-- src/hls.py nbr(); src/fires.py triangle_cutoff() -->

### 3.3 Three fixes for the spring leaf season
In spring the whole landscape turns green, so "no change" is no longer at zero. Each fix asks the same question: **did this pixel's score fall 0.10 more than normal?** They differ only in what "normal" means.

| Fix | "Normal" = the typical (median) change of ... | Uses the outline? |
|---|---|---|
| A, look-alikes | pixels with a similar NBR before the fire (20 groups) | No |
| B, ring | pixels in a ring 300 m to 2 km outside the outline | Yes |
| C, look-alikes + height | pixels with a similar NBR before AND similar height (10 x 5 groups) | No |

I used the median (middle value) so a few burned pixels in a group cannot drag "normal" far. I designed fix C after seeing where fix A failed, so it needed a fresh exam (Section 3.5).

<!-- src/09_grade_burn_maps.py (EXTRA = 0.10, GROUPS = 20); src/fires.py ring_mask(); src/10_ridge_check.py (10 x 5) -->

### 3.4 Answer keys
**Floods: my own blind labels.** I labeled 269 spots by eye on the NOAA airplane photos as water, not water, or can't tell.
- A plain random sample would hold almost no flood, because flood covers only a few percent of the box. So I picked a fixed number of spots from four groups: each map's flood, plus spots every map called dry (100, 50, 9 and 110 spots).
- This is a **stratified sample**, like polling each neighborhood separately. Each spot is then weighted by how much of the box its group covers.
- The labeling page never showed which map picked a spot, and the order was shuffled.
- I re-labeled 40 random spots a second time, without seeing my first answers, to check myself.

**Burns: official outlines** from the National Interagency Fire Center. I did not draw them.

<!-- src/04_make_label_sample.py; CLAUDE.md Step 4a (dark_nir 100, drop_only 50, radar_only 9, dry 110, seed 42) -->

### 3.5 Fair grading
- **Two grades, not one.** *Caught* (recall) = the share of real flood or burn the map found. *Right* (precision) = the share of its flags that were real. **F1** joins the two into one number. I did not use overall accuracy: in a mostly dry box, "say dry everywhere" scores 96%.
- **How much could luck move the grade?** I re-drew the labeled spots at random 2,000 times and re-scored. The middle 95% of the results is the range I report.
- **Machine learning took exams by area.** Two models (logistic regression and a random forest) learned from my labels, using 21 clues per pixel. I cut the box into 4 x 4 blocks and always tested on blocks the model never saw. Neighboring spots look almost the same, so testing on random spots lets a model peek.
- **A fresh exam.** I ran the whole burn recipe, unchanged, on a second fire (Great Lakes). I fixed the answer key, the photos and two predictions before looking at a single burn pixel.

<!-- src/05_score_maps.py (bootstrap n=2000, weights); src/06_machine_learning.py (BLOCKS = 4, 5 folds, 300 trees); results/05_map_scores.csv ("say dry everywhere" accuracy 0.960) -->

---

### Notes for me (delete before final)
**Explain back, out loud:**
1. What two things does every map need? (Hint: a score and a ...)
2. What does "normal" mean in fix A, and why did fix C need a fresh exam?
3. Why did I pick spots from four groups instead of fully at random?
4. Why test machine learning on whole blocks instead of random spots?

**Moved here from Section 2:** the band names (B03, B8A ...) can go in an appendix if there is room.
