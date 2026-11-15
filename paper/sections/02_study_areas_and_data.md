<!-- DRAFT 2 (Nov 15, 2026). Plainer wording after my first explain-back. Not final until I can explain it back. Every number has its source file in a comment. -->

## 2. Study areas and data

### 2.1 Three study areas
I worked in three small boxes in North Carolina, each about 20 to 30 km on a side (Figure 1).

![Figure 1. The three study areas. Blue: the flood box. Orange: the two fire boxes.](../../figures/12_locator_map.png)

**Figure 1.** The three study areas. Blue: the flood box. Orange: the two fire boxes. State outlines: U.S. Census Bureau.

- **Flood: the Lumber River at Lumberton** (23 x 17 km). Hurricane Florence made landfall on September 14, 2018, and the river flooded the town. The Lumber is a blackwater river: its water is tea-colored from dissolved plant matter.
- **Mountain fire: the Black Cove Complex** (18 x 17 km), on the South Carolina border. It started on March 19, 2025, and burned about 31 km².
- **Coastal fire: the Great Lakes fire** (22 x 30 km), in Croatan National Forest. It started on April 19, 2023, and burned about 130 km² of flat, swampy ground.

Each fire box is the official fire outline plus 3 km on every side, so it also holds forest that did not burn.

<!-- box sizes: src/12_locator_map.py output. Fire sizes: fires.py (31.1 and 130.1 km2). Landfall: README. -->

### 2.2 Satellite data: NASA HLS
Satellites like Landsat (USA) and Sentinel-2 (Europe) carry cameras that measure how much sunlight each patch of ground reflects. They also measure light our eyes cannot see, such as near-infrared (NIR). The satellites only measure. My own code decides what is water or burned (Section 3).

I used NASA's Harmonized Landsat Sentinel-2 (HLS) data, version 2.0. HLS cleans the photos from both satellite families and puts them on one 30 m grid, so they can be used as if one camera took them all. Together they photograph a place about every 2 to 3 days. That matters after a hurricane: more photos means more chances to catch a clear day.

I used four kinds of light: green, NIR, and two shortwave-infrared bands. Each HLS photo also comes with a cloud mask, which marks every pixel that is cloud or cloud shadow. I left those pixels out.

### 2.3 Choosing the photos
**Clouds were the main risk.** For each photo I measured how much of the **whole box** was clear. A photo does not always cover the whole box: sometimes the edge of the satellite's path cuts through it. My first count divided by only the part the photo covered, so a photo that saw just 2% of a box scored "97% clear". I fixed this and kept only photos at least 80% clear over the whole box.

**Before and after came from the same satellite.** The two satellite families have slightly different cameras. If I compared a Landsat photo with a Sentinel-2 photo, a change could come from the camera, not the ground. Using one satellite is like weighing yourself on the same scale both times.

| Study area | Before | After | Clear share of box (before / after) |
|---|---|---|---|
| Lumber River | Sentinel-2, Sept 6, 2018 | Sentinel-2, Sept 18, 2018 | 92% / 86% |
| Black Cove, March pair | Landsat, Mar 18, 2025 | Landsat, Mar 26, 2025 | 100% / 100% |
| Black Cove, April pair | Sentinel-2, Mar 11, 2025 | Sentinel-2, Apr 12, 2025 | 100% / 80% |
| Great Lakes, Landsat pair | Landsat, Apr 18, 2023 | Landsat, May 4, 2023 | 92% usable in both |
| Great Lakes, Sentinel-2 pair | Sentinel-2, Apr 10, 2023 | Sentinel-2, May 10, 2023 | 91% usable in both |

<!-- Lumber: results/01_clear_photos.csv. Black Cove: results/07_fire_photos.csv. Great Lakes: results/11_great_lakes_pair_facts.csv ("box usable"). -->

- **Lumberton** was the only one of three flooded river towns with a clear photo soon after the storm, four days after landfall. Fayetteville waited 17 days and Kinston 19.
- **Black Cove, March 26** was taken while the fire was still growing (until about March 31). **April 12** came after the fire stopped, but the spring leaves were already coming out.

<!-- results/01_summary.csv (4, 17, 19 days). -->

### 2.4 Other data
- **NOAA airplane photos** (Sept 19-20, 2018), taken one day after the flood photo. They are sharp enough to see flooded fields. I used them to build the flood answer key.
- **Sentinel-1 radar** (Sept 7 and 19, 2018), processed with the Alaska Satellite Facility's free HyP3 service. Radar sends its own pulse, so it sees through clouds. I used it as a second flood map.
- **Official fire outlines** from the National Interagency Fire Center: the answer key for the burn maps.
- **Ground height** from NASA's NASADEM, 30 m, to test why one fix failed in the mountains.

---

### Notes for me (delete before final)
**Explain back, out loud:**
1. What does the satellite do, and what does my code do?
2. Why measure the clear share over the whole box?
3. Why must the before and after photos come from the same satellite?

**Moved out of this section:** the band-name table (B03, B8A ...) goes to Methods or an appendix. The "auto-generated vs certified" outline note goes to Limits.
