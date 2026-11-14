# Written with Super Intelligence (SI) assistance.
"""Record the app as GIFs for the slides and the project page, by taking screenshots of it.

Opens the app in headless Chrome (through demo_shots.mjs) at one address per radar pass (the address holds the pass,
see app/src/link.ts), saves a screenshot of each, and joins them into a GIF. A second GIF
shows the "Where to check" view flat, in 3D, and with one block's evidence graph open.
The frames are the real app, not a mock-up.

Needs Google Chrome, Node, Pillow and requests. The project page takes GIFs up to 10 MB.

    python app/scripts/demo_gif.py --url https://tommyquak.github.io/GarugonsSpaceApps/ --out pipeline/out/figures
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

import certifi
import requests
from PIL import Image

SHOTS = Path(__file__).with_name("demo_shots.mjs")
VIEW = "v=9.0/-2.8300/114.2100"


def shots(urls, folder, size=(1280, 720), wait_ms=4500):
    """Screenshots of the app at each address, in order, as images."""
    subprocess.run(["node", str(SHOTS), str(folder), str(size[0]), str(size[1]), str(wait_ms), *urls], check=True, timeout=1800)
    return [Image.open(f).convert("RGB") for f in sorted(Path(folder).glob("shot_*.png"))]


def save_gif(frames, durations, path, width=960, colours=160):
    small = [f.resize((width, round(f.height * width / f.width)), Image.LANCZOS).quantize(colours, method=Image.MEDIANCUT, dither=Image.NONE) for f in frames]
    small[0].save(path, save_all=True, append_images=small[1:], duration=durations, loop=0, optimize=True)
    print(f"wrote {path}: {len(frames)} frames, {path.stat().st_size / 1e6:.1f} MB")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", required=True, help="address of the running app, ending in /")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    layers = requests.get(a.url + "layers/layers.json", timeout=60, verify=certifi.where()).json()
    passes = sorted({(x["date"], x["track"]) for x in layers if x.get("kind") == "pass"})
    season = ",".join(x["id"] for x in layers if x.get("kind") == "season")
    with tempfile.TemporaryDirectory() as tmp:
        urls = [f"{a.url}#{VIEW}&l={season}&d={date}.{track}" for date, track in passes] + [f"{a.url}#{VIEW}&l={season}"]
        frames = shots(urls, Path(tmp) / "season")
        save_gif(frames, [650] * len(passes) + [2600], a.out / "demo_season.gif")

        views = [("a=map", 2400), ("a=map,3d", 2800), ("a=map,list", 2800), ("v=10.8/-2.52/113.73&a=map&b=west-000-020", 3600), ("a=how", 3200)]
        urls = [f"{a.url}#{q}" if q.startswith("v=") else f"{a.url}#{VIEW}&l={season}&{q}" for q, _ in views]
        frames = shots(urls, Path(tmp) / "check", wait_ms=7000)
        save_gif(frames, [d for _, d in views], a.out / "demo_check.gif", colours=200)


if __name__ == "__main__":
    main()
