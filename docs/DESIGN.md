# Interface design

The design language of the app, and what the interface holds. The design language was set at the start of the weekend and has held; the second half describes the interface as built.

## Who it is for, and what they do with it

| Person | Question they bring | What they leave with |
|---|---|---|
| Field team | Where did the radar echo fall and stay low after the rain? | A list of 1 km blocks with coordinates that a visit could check |
| Fire analyst | Where was fire detected, on peat and off it? | The fire layer with its dates |
| Researcher, journalist, judge | Is this a real change, and how do you know? | The evidence for one place, and the limits |

Every screen serves one of three verbs: **interpret** (what am I looking at), **explore** (show me this place and this date), **take away** (give me something I can carry).

## Design language

1. **The map is the page.** Controls float over it and never cover more than a third of it. On a phone, one sheet at a time.
2. **One colour family per meaning, and nothing else uses it.**

   | Meaning | Colour | Use |
   |---|---|---|
   | The radar echo fell | Sand to dark brown | The fall layers, the passes on the slider |
   | Fire detected (NASA FIRMS) | Red | Fire layers, and the fire switch on the slider |
   | The echo rose after the rain | Blue ramp | The layers for the first pass after the rain |
   | Still low after the rain | Violet | The "left" layer |
   | Steady, reference, context | Greys; reference forest as a green outline | Everything that is not a finding |
   | Peat boundary | Thin white line; land outside it drawn at about a third strength | Always available as a switch |
   | The three levels of "Where to check" | Red, orange, pale yellow | That view only, where the other layers are hidden |

   The interface itself has no colour: text, lines, focus and selected states are ivory ink on dark. A selected control is filled, not outlined. Colour on screen therefore always means data. Red is never used for errors or alerts. The levels reuse red by exception, because fire detections decide the top level.
3. **Sentence first, chart second, table third.** Every place and every layer gets one plain sentence before any graphic, for example "HH fell 1.8 dB between the dry start in July and October, then rose 1.1 dB on the first pass after the rain".
4. **Say what was measured, not what we wish we measured.** Legends read "Fall in HH", never "dryness" or "water table". Every image carries its date, including the base map ("Sentinel-2 mosaic, 2016").
5. **Agreement is visible.** A stronger colour means more of the conditions for a class hold. A fall of less than 1 dB shows no colour.
6. **Limits are one tap away** from every screen. Numbers in the panels come from `validation.json`; the About page lists only those marked `final`.
7. **Plain type.** IBM Plex Sans (SIL Open Font Licence), served with the app. Body 14 px, small 12 px, headings 15 to 16 px. Tabular figures, sentence case, no capitals or letter-spacing for emphasis, and no label sitting above a heading.
8. **Motion only when it carries meaning:** the season playing, and the camera moving between places. It stops if the device asks for reduced motion.
9. **Usable by everyone:** text contrast of 4.5 to 1 or better, visible keyboard focus, touch targets of 44 px, ramps checked for colour-blind viewers, every chart with a table behind it.

## The interface as built

### Interpret
- **The entry view.** An illustrative room with the live map on its main screen. The scene was made with Super Intelligence (SI) and is labelled as such; it can be skipped.
- **The opening story.** Seven beats on a first visit: photographs of fire and canals, the same week seen by a camera and by the radar, then the season and the view of where to check on the live map. It can be replayed from "Story".
- **How it decides.** The ontology drawn as a graph: sources, observations, states and classes, each with its rule and thresholds.
- **Limits and About.** `docs/LIMITS.md` in a panel, and the checked numbers with where each comes from.

### Explore
- **The season.** A slider over every radar pass on both orbits, with play, the date and the orbit always in view, a switch for fire detected up to each date, and a small chart of how the echo, the reference forest, fire and rain moved through the season.
- **Place card** on click: the reading sentence, the chart (HH and HV, both orbits, rain bars, fire dates), a table, and actions: fly down, an optical image for a chosen date, add to my places, copy coordinates, open in OpenStreetMap.
- **Fly down.** The camera tilts to an oblique view over the chosen place and circles it slowly. See "Why not street level" below.
- **Explore the data.** The single layers behind the views, with a legend each.
- **Link to this view.** The address bar always holds the place, date and layers, so a view can be sent to someone.

### Take away
- **Where to check.** Every classed 1 km block in one of three levels, flat or as columns whose height is the level, with a ranked list and its filters. In 3D, the blocks of one level that touch are drawn as one shape with slightly rounded corners; the block under the pointer and the selected block still show as single blocks. The order inside a class is by the size of the fall, which is not a grade of the land.
- **Export.** The list as CSV and GeoJSON, ready for a GPS or a GIS.
- **Field assessment.** Three pages to print: a map of the blocks, the evidence, and a table of blocks to visit with a box to tick.

## Why not street level

A walk-around view at ground level is not possible here, and pretending would mislead:

- **No open ground-level imagery exists for these peatlands,** and the rules require every material to be openly licensed.
- **Our sharpest data is 10 m per pixel** (optical) and 50 m (radar). At eye level one radar pixel would fill the whole view.
- **The land is flat.** A peat dome rises a few metres over many kilometres, so 3D terrain adds almost nothing.

What does work: the oblique fly-down, which gives the sense of descending to a place, and the optical image, which shows real imagery of that spot on a real date. On many dry-season days that image shows cloud or smoke.

## Open materials used

MapLibre GL JS (BSD). Sentinel-2 cloudless 2016 by EOX (CC BY 4.0). NASA GIBS imagery (open). OpenStreetMap (ODbL). IBM Plex Sans (SIL OFL). No commercial map tiles. The full list is in `submission/LICENCES.md`.
