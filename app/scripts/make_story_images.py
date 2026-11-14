# Written with Super Intelligence (SI) assistance.
"""Real images for the opening story (app/src/opening.ts), each with its credit.

Ground photographs come from Wikimedia Commons, by title, with the author, licence and source
page read from the Commons record and never typed by hand. Satellite images come from NASA GIBS
(VIIRS true colour) and from the NISAR stacks this repository builds. Writes, under --out:

    <name>.jpg      each image, at most 1920 px wide
    credits.json    for each image: what it shows, where, when, who made it, licence, source
    CREDITS.md      the same as a table

Every photograph is openly licensed (CC BY or CC BY-SA). They are resized and re-compressed,
nothing else; under CC BY-SA the resized copies carry the same licence.

    python app/scripts/make_story_images.py --stacks pipeline/out/stacks --out app/public/story
"""
import argparse
import io
import json
import re
from pathlib import Path

import certifi
import numpy as np
import requests
from PIL import Image
from rasterio.transform import Affine, from_origin
from rasterio.warp import Resampling, reproject

AGENT = {"User-Agent": "dry-season-waltz-build/1.0 (open-source student project)"}
COMMONS = "https://commons.wikimedia.org/w/api.php"
GIBS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
WIDTH = 1920

# name -> Commons file title. What each shows and where is read from its Commons page.
PHOTOS = {
    "fire": "File:Marking the Fire.jpg",
    "burnt": "File:Batlefield.jpg",
    "canal": "File:Kalimantan deforestation and degradation 8 (10706239044).jpg",
    "open": "File:Kalimantan deforestation and degradation 4 (10706228444).jpg",
    "forest": "File:Peat Forest Swamp (10712654875).jpg",
}
SMOKE_DAY = "2026-09-19"                    # a day of heavy smoke over southern Borneo
SMOKE_BOX = (110.6, -4.7, 117.1, -0.5)      # west, south, east, north
RADAR_DAY = "2026-09-14"                    # a dawn pass of track 125
RADAR_BOX = (113.6, -3.0, 114.83, -2.42)   # the band both study boxes cover, so the picture has no empty corner


def plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def save(image, path):
    image = image.convert("RGB")
    if image.width > WIDTH:
        image = image.resize((WIDTH, round(image.height * WIDTH / image.width)), Image.LANCZOS)
    image.save(path, "JPEG", quality=80, optimize=True, progressive=True)
    return image.size


def commons(titles):
    r = requests.get(COMMONS, headers=AGENT, timeout=120, verify=certifi.where(), params={
        "action": "query", "format": "json", "titles": "|".join(titles), "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": WIDTH})
    r.raise_for_status()
    return {p["title"]: p["imageinfo"][0] for p in r.json()["query"]["pages"].values() if "imageinfo" in p}


def gibs(day, box, width, height):
    west, south, east, north = box
    r = requests.get(GIBS, headers=AGENT, timeout=180, verify=certifi.where(), params={
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": "VIIRS_NOAA20_CorrectedReflectance_TrueColor",
        "CRS": "EPSG:4326", "BBOX": f"{south},{west},{north},{east}", "WIDTH": width, "HEIGHT": height, "FORMAT": "image/jpeg", "TIME": day})
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content))


def radar(stacks, day, box, width, height):
    """NISAR HH in decibels for one pass over `box`, as a grey image."""
    west, south, east, north = box
    grid = from_origin(west, north, (east - west) / width, (north - south) / height)
    out = np.full((height, width), np.nan, "float32")
    for stack in sorted(Path(stacks).glob("*_125.npz")):
        z = np.load(stack)
        dates = [str(d) for d in z["dates"]]
        if day.replace("-", "") not in dates or stack.name.startswith("gauges"):
            continue
        part = np.full((height, width), np.nan, "float32")
        reproject(z["hh"][dates.index(day.replace("-", ""))], part, src_transform=Affine(*z["T"]), src_crs=f"EPSG:{int(z['crs'])}", src_nodata=np.nan,
                  dst_transform=grid, dst_crs="EPSG:4326", dst_nodata=np.nan, resampling=Resampling.average)
        out = np.where(np.isfinite(part), part, out)
    grey = np.clip((out + 14) / 11, 0, 1)          # -14 dB black to -3 dB white
    grey = np.where(np.isfinite(out), grey, 0.05)
    return Image.fromarray((grey * 255).astype("uint8"), "L")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    credits = {}

    found = commons(list(PHOTOS.values()))
    for name, title in PHOTOS.items():
        info = found[title]
        meta = info["extmetadata"]
        licence = plain(meta["LicenseShortName"]["value"])
        if not licence.startswith(("CC BY", "CC0", "Public domain")) or "NC" in licence or "ND" in licence:
            raise SystemExit(f"{title}: licence {licence!r} is not open enough to ship")
        raw = requests.get(info["thumburl"], headers=AGENT, timeout=180, verify=certifi.where())
        raw.raise_for_status()
        size = save(Image.open(io.BytesIO(raw.content)), a.out / f"{name}.jpg")
        credits[name] = {"file": f"{name}.jpg", "kind": "photograph", "author": plain(meta.get("Artist", {}).get("value", "")),
                         "licence": licence, "licence_url": meta.get("LicenseUrl", {}).get("value", ""),
                         "date": plain(meta.get("DateTimeOriginal", {}).get("value", ""))[:10], "title": title[5:],
                         "description": plain(meta.get("ImageDescription", {}).get("value", "")), "source": info["descriptionurl"],
                         "changes": "Resized and re-compressed.", "size": list(size)}
        print(f"{name}.jpg {size[0]}x{size[1]} | {credits[name]['author']} | {licence} | {credits[name]['date']}")

    west, south, east, north = SMOKE_BOX
    size = save(gibs(SMOKE_DAY, SMOKE_BOX, WIDTH, round(WIDTH * (north - south) / (east - west))), a.out / "smoke.jpg")
    credits["smoke"] = {"file": "smoke.jpg", "kind": "satellite image", "author": "NASA EOSDIS GIBS, VIIRS on NOAA-20", "licence": "NASA open data",
                        "licence_url": "https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance", "date": SMOKE_DAY,
                        "title": "Southern Borneo in true colour", "description": "VIIRS corrected reflectance, true colour.",
                        "source": "https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api", "changes": "None.", "size": list(size)}
    west, south, east, north = RADAR_BOX
    height = round(1600 * (north - south) / (east - west))
    for name, image, author, what in (("optical", gibs(RADAR_DAY, RADAR_BOX, 1600, height), "NASA EOSDIS GIBS, VIIRS on NOAA-20", "VIIRS corrected reflectance, true colour, over the study boxes."),
                                      ("radar", radar(a.stacks, RADAR_DAY, RADAR_BOX, 1600, height), "NASA and ISRO, NISAR L2 GCOV from ASF DAAC", "NISAR L-band HH backscatter, -14 to -3 dB, over the study boxes. Built by pipeline/radar.")):
        size = save(image, a.out / f"{name}.jpg")
        credits[name] = {"file": f"{name}.jpg", "kind": "satellite image", "author": author, "licence": "NASA open data",
                         "licence_url": "https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance", "date": RADAR_DAY,
                         "title": "The study boxes on one day", "description": what, "source": "https://search.asf.alaska.edu" if name == "radar" else "https://www.earthdata.nasa.gov",
                         "changes": "None.", "size": list(size)}
    for name in ("smoke", "optical", "radar"):
        print(f"{name}.jpg {credits[name]['size'][0]}x{credits[name]['size'][1]} | {credits[name]['author']} | {credits[name]['date']}")

    (a.out / "credits.json").write_text(json.dumps(credits, indent=1, ensure_ascii=False) + "\n")
    rows = ["# Image credits", "", "Images of the opening story, made by `app/scripts/make_story_images.py`. Photographs are from Wikimedia Commons under the licence shown.", "",
            "| File | Shows | Author | Date | Licence | Source | Changes |", "|---|---|---|---|---|---|---|"]
    for c in credits.values():
        rows.append(f"| `{c['file']}` | {c['description'][:140]} | {c['author']} | {c['date']} | [{c['licence']}]({c['licence_url']}) | [source]({c['source']}) | {c['changes']} |")
    (a.out / "CREDITS.md").write_text("\n".join(rows) + "\n")
    total = sum(f.stat().st_size for f in a.out.glob("*.jpg"))
    print(f"{len(credits)} images, {total / 1e6:.1f} MB in {a.out}")


if __name__ == "__main__":
    main()
