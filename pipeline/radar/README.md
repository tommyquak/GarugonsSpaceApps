# Radar data and stacks (track 1)

Turns NISAR L2 GCOV granules into one stack per site and track, in the format of `docs/DATA_CONTRACT.md` section 1.

## Get the stacks

The built stacks are attached to GitHub releases: the dawn orbit (125) in `data-v1`, the dusk orbit (061) in `data-v5`. Most people only need this:

```
gh release download data-v1 --repo tommyquak/GarugonsSpaceApps --dir pipeline/out/stacks --pattern '*_125.npz'
gh release download data-v5 --repo tommyquak/GarugonsSpaceApps --dir pipeline/out/stacks --pattern '*_061.npz'
```

```python
import numpy as np
z = np.load("pipeline/out/stacks/west_125.npz")
hh, hv = z["hh"], z["hv"]            # decibels, shape (dates, rows, cols), NaN where there is no data
dates = [str(d) for d in z["dates"]]  # YYYYMMDD
T, epsg = z["T"], int(z["crs"])       # x = T[0] * col + T[2], y = T[4] * row + T[5] (pixel corner)
```

## Rebuild them from NASA's archive

Needs a NASA Earthdata login in `~/.netrc`. The pull reads only the part of each granule that covers the site, about 180 MB per polarisation for the west box instead of 2 GB.

```
python pipeline/radar/pull_gcov.py --site west --out data/gcov/west
python pipeline/radar/build_stack.py --src data/gcov/west --track 125 --out pipeline/out/stacks/west_125.npz
python pipeline/radar/build_stack.py --src data/gcov/west --track 61  --out pipeline/out/stacks/west_061.npz --like pipeline/out/stacks/west_125.npz
```

Sites and their boxes are in `sites.json`.

## What to know about the stacks

- **Two orbits, one grid.** Track 125 passes at dawn going north (ascending). Track 061 passes at dusk going south (descending). NISAR delivers them on different UTM zones, so the 061 stack is resampled onto the 125 grid. Both stacks of a site line up pixel for pixel.
- **50 m pixels.** Each is the average of 25 samples of 10 m, taken in linear power before the conversion to decibels.
- **Dates differ between orbits.** The two orbits never pass on the same day. Each stack carries its own date list.
- **Dual polarisation only.** Passes that recorded HH alone are left out.
- **Not corrected for anything else.** No terrain, rain or calibration adjustment is applied here. Track 2a removes scene-wide shifts with the intact-forest baseline.
