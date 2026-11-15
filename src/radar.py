"""Radar helpers: get cleaned-up Sentinel-1 radar images from NASA's free HyP3 service.

Raw radar is warped by the satellite's slanted view and by hills. HyP3's "RTC" processing
(radiometric terrain correction) straightens it onto a normal map grid. It runs on NASA's
computers using the Earthdata login saved in ~/.netrc.
"""
import zipfile
from pathlib import Path

import hyp3_sdk

ROOT = Path(__file__).resolve().parents[1]
RADAR_DIR = ROOT / "data" / "radar"  # git-ignored

# Same satellite (Sentinel-1A) and same orbit (path 77, ascending), 12 days apart, so both
# pictures are taken from the same angle. Both cover 100% of the Lumber River box.
# (First try used path 150, Sept 12 / Sept 18: those scenes only grazed the box's corner,
#  covering 6% and 0% of it, so every pixel came back blank. check_coverage() now guards this.)
SCENES = {
    "before": "S1A_IW_GRDH_1SDV_20180907T231350_20180907T231415_023599_02922C_5F84",  # Sept 7, 2018
    "after": "S1A_IW_GRDH_1SDV_20180919T231350_20180919T231415_023774_0297CC_B86C",   # Sept 19, 2018
}
JOB_PREFIX = "nc-hls-p77-"


def check_coverage(bbox, minimum=0.99):
    """Stop early if a scene's real footprint does not cover the box (touching is not enough)."""
    import asf_search as asf
    from shapely.geometry import box, shape
    b = box(*bbox)
    for label, scene in SCENES.items():
        fp = shape(asf.granule_search([scene])[0].geometry)
        share = fp.intersection(b).area / b.area
        print(f"{label}: {scene[17:25]} covers {share:.0%} of the box")
        if share < minimum:
            raise RuntimeError(f"{label} scene covers only {share:.0%} of the box")


def local_vv(label):
    """Path of the downloaded VV image for 'before' or 'after', or None if not downloaded yet."""
    found = sorted(RADAR_DIR.glob(f"{label}/*/*_VV.tif"))
    return found[0] if found else None


def fetch_all():
    """Submit HyP3 jobs for any scene not downloaded yet, wait, download and unzip."""
    import hls
    check_coverage(hls.STUDY_AREAS[hls.STUDY_AREA])
    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    todo = {k: v for k, v in SCENES.items() if local_vv(k) is None}
    if not todo:
        print("Both radar images already downloaded.")
        return
    hyp3 = hyp3_sdk.HyP3()  # signs in with ~/.netrc; never prints the password
    jobs = hyp3_sdk.Batch()
    for label, scene in todo.items():
        # Reuse a job we already submitted earlier for this scene (saves processing credits).
        old = [j for j in hyp3.find_jobs(name=f"{JOB_PREFIX}{label}") if j.succeeded() or j.running()]
        if old:
            print(f"{label}: reusing earlier job {old[0].job_id}")
            jobs += old[0]
        else:
            print(f"{label}: submitting {scene}")
            jobs += hyp3.submit_rtc_job(
                scene, name=f"{JOB_PREFIX}{label}",
                resolution=30,          # match the 30 m HLS pixels
                scale="decibel",        # radar brightness in dB: water is very negative
                speckle_filter=True,    # smooth radar's grainy "salt and pepper" noise
                radiometry="gamma0",
            )
    print("Waiting for NASA to process (often 10-30 minutes)...")
    jobs = hyp3.watch(jobs)
    for job in jobs:
        label = job.name.replace(JOB_PREFIX, "")
        if not job.succeeded():
            raise RuntimeError(f"HyP3 job for {label} failed: {job.status_code}")
        for zpath in job.download_files(RADAR_DIR / label):
            with zipfile.ZipFile(zpath) as z:
                z.extractall(RADAR_DIR / label)
            zpath.unlink()  # keep only the unzipped files
        print(f"{label}: downloaded {local_vv(label).name}")


if __name__ == "__main__":
    fetch_all()
