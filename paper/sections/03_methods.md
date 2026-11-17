<!-- DRAFT 2 (Nov 17, 2026). Rewritten with everyday examples after my first explain-back did not pass. Not final until I can explain it back. Every number has its source in a comment. Budget: 1.25 pages (this draft is longer on purpose; some examples may be cut for the final). -->

## 3. Methods

Every map in this paper is made with the same three steps: give each pixel a **score**, draw a **cutoff** line, then **grade** the map against an answer key.

> **In everyday terms: a thermometer.** The thermometer gives each person a number (the score). A doctor draws a line at 100.4 °F: above it is "fever" (the cutoff). Move the line to 99 °F and many more people suddenly "have a fever", even though nobody's temperature changed. Maps work the same way: the satellite gives the numbers, and the line I draw decides what gets flagged.

### 3.1 Flood maps
**Score: how much near-infrared (NIR) light came back.** Water swallows NIR light, the way a black T-shirt soaks up sunlight on a hot day. So water pixels have a low NIR number.

**Flood = water after the storm that was not water before.** Think of a driveway after a rainstorm. The pond in the yard was always there, so it is not news. The new puddles are what we want. I made a water map for the photo before and the photo after, then kept only the new water.

I tried three water rules:
- **Textbook indexes (NDWI, MNDWI).** They compare green light with NIR or shortwave infrared, and say "water" when the index is above 0.
- **Dark in NIR.** Water = NIR below 0.10.
- **NIR fell by half.** Flood = NIR after is less than half of NIR before.

I picked the 0.10 line from the bar chart of every pixel's NIR value, before looking at any answer key. Pixels hidden by cloud or cloud shadow on either day were left out.

<!-- rules and cutoffs: src/02_water_maps.py (NIR_DARK = 0.10, ratio < 0.5) -->

### 3.2 Burn maps
**Score: the Normalized Burn Ratio (NBR).** A healthy green lawn reflects lots of NIR light and little shortwave infrared. A patch scorched by a grill does the opposite. NBR compares the two, so it is high for living plants and low for burned ground.

The burn score is **dNBR = NBR before minus NBR after**. A big drop means burned.

I drew the line in two ways, both without looking at the fire outline:
- **Textbook line:** dNBR above 0.10.
- **Histogram line (the triangle method).** Picture every pixel's score stacked up as a bar chart. Most of the box did not burn, so those pixels form one tall hill near "no change". The burned pixels trail off to one side like a long, thin tail. Stretch a string from the top of the hill to the end of the tail. The line goes where the bars sag furthest below the string: the foot of the hill.

<!-- src/hls.py nbr(); src/fires.py triangle_cutoff() -->

### 3.3 Three fixes for the spring leaf season
**The problem.** Between the before and after photos, spring arrived and the whole forest turned green. Every pixel's score moved, burned or not. So "no change" was no longer at zero.

> **In everyday terms: electric bills in a heat wave.** In a heat wave, every apartment's electric bill goes up, because everyone runs the air conditioning. If you want to find the apartment with a broken, leaking AC unit, you cannot just look for "a bill that went up". You look for a bill that went up **much more than normal**. The hard part is deciding what "normal" is.

Each fix asks the same question: **did this pixel's burn score (dNBR) rise 0.10 more than normal?** In other words, did its NBR drop more than its neighbors' did? They differ only in who counts as "normal".

| Fix | "Normal" = the middle change of ... | Apartment version | Uses the outline? |
|---|---|---|---|
| A, look-alikes | pixels that looked like it before the fire (20 groups, by NBR before) | apartments of the same size | No |
| B, ring | pixels in a ring 300 m to 2 km outside the outline | the buildings right next door | Yes |
| C, look-alikes + height | pixels with a similar NBR before AND a similar height (10 x 5 groups) | same size AND same floor (top floors get hotter) | No |

**Why the middle value (median).** Line up every bill in a group from lowest to highest and take the one in the middle. One huge bill from the broken AC cannot drag the middle very far. In the same way, a few burned pixels in a group cannot drag "normal" far.

**Why fix C needed a fresh exam.** I designed fix C *after* seeing where fix A went wrong on Black Cove. That is like adjusting a recipe in your own kitchen until it tastes right: of course it works there. The real test is cooking it, unchanged, in someone else's kitchen (Section 3.5).

<!-- src/09_grade_burn_maps.py (EXTRA = 0.10, GROUPS = 20); src/fires.py ring_mask(); src/10_ridge_check.py (10 x 5) -->

### 3.4 Answer keys
**Floods: my own blind labels.** I looked at 269 spots on the NOAA airplane photos and marked each as water, not water, or can't tell.

- **Why not fully random spots.** Flood covers only a few percent of the box. Imagine a jar of 1,000 jelly beans with only 40 red ones. Grab 25 at random and you may get one red bean, or none, so you learn nothing about the reds. So I scooped from each group on purpose: spots each map called flood, plus spots every map called dry (100, 50, 9 and 110 spots). This is a **stratified sample**.
- **Putting the jar back together.** Each spot is then counted by how big its group really is. The dry group covers most of the box, so each dry spot counts for many more pixels than a flood spot.
- **Blind, like a taste test.** In a fair cola taste test, the cups have no labels, so you cannot favor your brand. My labeling page never showed which map picked a spot, and the spots came in shuffled order.
- **Checking myself.** I labeled 40 random spots a second time, without seeing my first answers.

**Burns: official outlines** from the National Interagency Fire Center. I did not draw them.

<!-- src/04_make_label_sample.py; results/04_labels.csv (dark_nir 100, drop_only 50, radar_only 9, dry 110; seed 42) -->

### 3.5 Fair grading
**Two grades, not one: a metal detector on the beach.**
- **Caught (recall):** of all the coins buried in the sand, how many did the detector beep on?
- **Right (precision):** of all its beeps, how many were really coins, not bottle caps?
- **F1** joins the two into one number, so a map cannot score well by being good at only one.
- **Why not "overall accuracy".** A detector that never beeps is "right" about almost every patch of sand, because most sand has no coin. In the same way, "say dry everywhere" scores 96% accuracy while finding no flood at all.

**How much could luck move the grade?** I re-drew the labeled spots at random 2,000 times and graded each new draw. Like re-shuffling a deck many times, this shows how much the result changes by chance. The middle 95% of the results is the range I report.

**Machine learning took exams on new areas.** Two models (logistic regression and a random forest) learned from my labels, using 21 clues per pixel. Two spots side by side in one flooded field look almost the same. If one is in the practice set and the other on the exam, it is like a test whose questions are copied from the homework with one number changed: you score high without learning anything. So I cut the box into 4 x 4 blocks, and every exam used only blocks the model had never seen.

**A fresh exam on a second fire.** I ran the whole burn recipe, unchanged, on the Great Lakes fire: the "someone else's kitchen" test. Before looking at a single burn pixel, I fixed the answer key, the photos and two predictions.

<!-- src/05_score_maps.py (bootstrap n=2000, weights); src/06_machine_learning.py (BLOCKS = 4, 5 folds, 300 trees); results/05_map_scores.csv ("say dry everywhere" accuracy 0.960) -->

---

### Notes for me (delete before final)
**Explain back, in my own words (no quiz):** for each part, say what it does and give the example.
- 3.1-3.2: score and cutoff (thermometer), flood = new water (driveway puddles).
- 3.3: "normal" and the three fixes (electric bills), why fix C needed a fresh exam (recipe in another kitchen).
- 3.4: why four groups (jelly beans), blind labeling (taste test).
- 3.5: caught vs right (metal detector), exams on new areas (copied homework).

**For the final version:** keep one or two examples and cut the rest to fit 1.25 pages. The band names (B03, B8A ...) can go in an appendix.
