# The demo slides

Seven slides, the demo limit. The thread through all seven: drained peat burns, the dry season hides it from cameras, and a radar that does not stop for cloud or smoke shows where the ground changed.

## The deck as built

The deck is made by `submission/build_slides.py` (a `.pptx` for Google Slides) and `submission/build_html_deck.py` (one HTML page). The words are lists in `build_slides.py` that both builders read. As built on 15 November 2026:

1. Title: the project in one sentence, the team and its members, the challenge.
2. The problem: how peat is degraded, in three photographs (wet, drained, burnt), what it costs, and why nobody can watch it in the dry season.
3. What the radar is and what it measures: an optical satellite and NISAR over the same place on one day, and the animation of the echo.
4. How the map is made, in five plainly worded steps, with the season in one picture, the three numbers that came out, and one line of technical terms.
5. The app in four recordings: the season, "Where to check" in 3D, the ontology under "How it decides", the field assessment.
6. How far to trust it, in short (two orbits agree, the audit, not ground truth), beside what a restoration agency can do with it: take the list, visit the top of it, restore where the visit confirms it, look again next season. The map does not choose the remedy.
7. What comes next, in order: ground truth, more seasons, subsidence as a second layer (a plan, not a result), and handing it over. Then the links.

The guide for the demo asks for the team name, the names of the team members and the challenge; they are on slides 1 and 7.

Build the final deck with `--final`; all six numbers it reads are `final` entries. The figures and recordings come from the release `figures-v3`; the photographs are those of the app's opening story (`app/public/story/`, credits in `CREDITS.md` there).
