# Interface design

The design language and the plan for the end-user interface. Track 4 owns the app and decides how to build it; this file says what it should feel like, what it must let a person do, and in what order to build. Proposed by the lead; change it on the board.

## Who it is for, and what they do with it

| Person | Question they bring | What they leave with |
|---|---|---|
| Restoration planner (canal blocking) | Which drained blocks dried hardest this season? | A ranked list of places with coordinates |
| Fire patrol lead | Where is it dry and not yet burnt? | A short list to patrol first |
| Researcher, journalist, judge | Is this real, and how do you know? | The evidence for one place, and the limits |

Every screen serves one of three verbs: **interpret** (what am I looking at), **explore** (show me this place and this date), **act** (give me something I can take away).

## Design language: "one colour, one meaning"

1. **The map is the page.** Controls float over it and never cover more than a third of it. On a phone, one sheet at a time.
2. **One colour family per beat of the story, and nothing else uses it.**

   | Meaning | Colour | Use |
   |---|---|---|
   | The radar echo fell | Sand to dark brown | Dry-down layers, slider passes |
   | A fire was detected | Red | Fire layers, and the fire switch on the slider |
   | Rewet: the echo rose after rain | Blue ramp | Recovery layers |
   | What the rain did not bring back | Violet | The "left" layer |
   | Steady, reference, context | Greys; reference forest as a green outline | Everything that is not a finding |
   | Peat boundary | Thin white line; land outside it drawn at about a third strength | Always available as a switch |

   | How affected (the at-a-glance levels) | Red, orange, pale yellow | "Where to check" |

   The interface itself has no colour: text, lines, focus and selected states are ivory ink on dark. A selected control is filled, not outlined. Colour on screen therefore always means data. Red is never used for errors or alerts.
3. **Sentence first, chart second, table third.** Every place and every layer gets one plain sentence before any graphic, for example "HH fell 1.8 dB from June to October and rose 1.1 dB after the rain".
4. **Say what was measured, not what we wish we measured.** Legends read "Fall in HH radar brightness, dB", never "dryness" or "water table". Every image carries its date, including the basemap ("Sentinel-2 mosaic, 2016").
5. **Confidence is visible.** Seen by both orbits: solid colour. Seen by one orbit only: lighter. Below the noise floor: no colour at all.
6. **Limits are one tap away** from every screen, and numbers appear only when `validation.json` marks them `final`.
7. **Quiet type.** IBM Plex Sans (SIL Open Font Licence), served with the app. Body 14 px, small 12 px, headings 15 to 16 px. Tabular figures everywhere, sentence case, no capitals or letter-spacing for emphasis, and no label sitting above a heading.
8. **Motion only when it carries meaning:** the season playing, and the camera moving between places. It stops if the device asks for reduced motion.
9. **Usable by everyone:** text contrast of 4.5 to 1 or better, visible keyboard focus, touch targets of 44 px, ramps checked for colour-blind viewers, every chart with a table behind it.

## The interface in three parts

### 1. Interpret: the guided story
Five cards, each flies the map to a prepared view with the right layers on.

1. **How to read this map.** What the radar sees, what the colours mean, in three sentences and one small diagram.
2. **Dry.** The west box in October. The forest holds still; drained land falls.
3. **Burn.** The fire layer over the dry-down. Fire on peat and fire off peat, both shown.
4. **Rewet.** After the rain: what came back (blue) and what did not (violet). HH against HV.
5. **What we cannot see.** The limits, and what NISAR could do with more years.

### 2. Explore: map, time and place
- **Season slider** with play, both orbits, the date and "dawn pass" or "dusk pass" always in view.
- **Compare:** a swipe handle between two states: June against October, or radar against the optical image.
- **Place card** on click: the reading sentence, the chart (HH and HV, both orbits, rain bars, fire dates), a table, and three actions: fly down, ground look, add to list.
- **Fly down.** The camera tilts to an oblique view low over the chosen place and circles it slowly, with the colour layer draped on the 10 m optical mosaic. This is the honest version of "go down and look": see "Why not street level" below.
- **Ground look.** A small second map locked to the same spot showing NASA optical imagery for a date you pick (HLS at 30 m where it exists, VIIRS or MODIS daily otherwise). On most dry-season days it shows cloud or smoke. That is the point: it shows why radar is needed, and on clear days it shows burn scars the radar also flagged.
- **Link to this view.** The address bar always holds the place, date and layers, so a view can be sent to someone.

### 3. Act: take something away
- **Watch list.** Blocks ranked by how far they fell, with filters: on mapped peat, no fire detected yet, both orbits agree. Each row has the fall in dB, area, coordinates, and whether it came back after the rain. Click a row to fly there.
- **My places.** Pins the user adds from place cards, kept in the browser.
- **Export.** The watch list or pinned places as CSV and GeoJSON, ready for a GPS or a GIS.
- **Place report.** One printable page for a place: map, reading, chart, limits. For handing to someone who decides.
- **Take me there.** Coordinates to copy, and a link that opens the spot in OpenStreetMap.

## Why not street level

A walk-around view like the one in Google Earth is not possible here, and pretending would mislead:

- **No open ground-level imagery exists for these peatlands,** and the rules require every material to be openly licensed, which rules out Google's.
- **Our sharpest data is 10 m per pixel** (optical) and 50 m (radar). At eye level one radar pixel would fill the whole view.
- **The land is flat.** A peat dome rises a few metres over many kilometres, so 3D terrain adds almost nothing.

What does work, and reads as "going down to look": the oblique fly-down, which gives the sense of descending to a place, and the ground look, which shows real imagery of that spot on a real date.

## Build order

| Priority | Piece | Why now |
|---|---|---|
| Must, Saturday | Colour system applied (burn, peat boundary, off-peat fade); reading sentences everywhere; link to this view | Makes the map correct and shareable |
| Must, Saturday night | Watch list with filters and export | It is the "actionable" part the challenge asks for |
| Should, Sunday morning | Compare swipe; fly down; five-card story | Exploration and the wow moment |
| If time | Ground look; place report; my places | Depth |

Cut from the bottom. Never cut: the slider, the place card, the watch list, the limits.

## Open materials used

MapLibre GL JS (BSD). Sentinel-2 cloudless 2016 by EOX (CC BY 4.0). NASA GIBS imagery (open). OpenStreetMap (ODbL). Terrain, if used: Terrain Tiles on AWS from open elevation data. No Google, Esri, Mapbox or Planet tiles.
