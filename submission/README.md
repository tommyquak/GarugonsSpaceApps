# Submission

What goes on the project page, and the documents behind it.

| File | What it is |
|---|---|
| `PAGE.md` | The text of the project page, field by field |
| `IMPACT.md` | Who would use this, for which decision, and what is still missing |
| `build_slides.py`, `build_html_deck.py` | Build the seven demo slides as a `.pptx` and as one HTML page; every number is read from `app/public/validation.json` |
| `SLIDES.md` | The deck as built, slide by slide |
| `../app/public/deck/` | The demo itself: the HTML deck as built with `--final`, served at `/deck/` on the site. Rebuild it with `python submission/build_html_deck.py --out app/public/deck --final` after any change to the deck |
| `LICENCES.md` | Everything we ship, with its licence and where the credit is shown |
| `SI_USE.md`, `si_use/` | How Super Intelligence (SI) was used, and one log per team member |

The demo is at most 7 slides or 30 seconds of video, hosted outside the Space Apps site at a link anyone can open. Every number on the page and the slides is a `final` entry in `app/public/validation.json`.
