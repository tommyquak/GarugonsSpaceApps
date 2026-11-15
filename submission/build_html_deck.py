# Written with Super Intelligence (SI) assistance.
"""Build the seven-slide demo deck as one HTML page (track 6), in the app's dark look.

Same slides, order and wording as build_slides.py, which makes the .pptx: the words are lists in that file
and both builders read them. This one makes a web deck with a fixed 1920 x 1080 stage scaled to any screen.
Every number of ours is read from validation.json through build_slides.Numbers; none is typed here.

    python submission/build_html_deck.py --figures submission/figures --out submission/deck
        # writes index.html and copies the pictures to assets/
    python submission/build_html_deck.py ... --final   # only keys marked final; no draft badge

Pictures: gh release download figures-v3 --dir submission/figures (the figures and the four app recordings).
The photographs are the ones of the app's opening story, in app/public/story, with their credits.
"""
import argparse
import html
import shutil
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_slides import (APP_URL, CAME_OUT, CODE_URL, EVENT, HOLDS, LEAD, LIMITS, MEMBERS, NEXT, PEAT, PEAT_SUM,  # noqa: E402
                          RADAR, RADAR_TITLE, SOURCES, STEPS, TEAM, VIEWS, Numbers, ontology_counts, ontology_words, rise_words)

PICTURES = ["fig_cloud.png", "explainer.gif", "fig_season.png", "fig_orbits.png"] + [v[0] for v in VIEWS]
PHOTOS = ["fire.jpg"] + [p[0] for p in PEAT]


def copy_pictures(fig, photos, assets):
    """Copy the figures and recordings next to the page, and the photographs at the size the slides show them."""
    assets.mkdir(parents=True, exist_ok=True)
    for name in PICTURES:
        shutil.copyfile(fig / name, assets / name)
    for name in PHOTOS:
        img = Image.open(photos / name).convert("RGB")
        img.thumbnail((1920, 1280) if name == "fire.jpg" else (1100, 740))
        img.save(assets / name, quality=84, optimize=True)


def numbers(num):
    """Every number of ours on the deck, keyed for the page template."""
    rise, rise_where = rise_words(num)
    return {
        "west_km2": num.km2("fell_1db_km2_on_peat_west"),
        "east_km2": num.km2("fell_1db_km2_on_peat_east"),
        "rise": rise,
        "rise_where": rise_where,
        "r_west": f"{num.get('track5_west_orbit_spearman'):.2f}",
        "r_east": f"{num.get('track5_east_orbit_spearman'):.2f}",
    }


def e(words):
    return html.escape(words)


def page(n, draft, counts):
    """The deck. Lists from build_slides.py become the parts of each slide; {{key}} slots take the numbers."""
    out = TEMPLATE
    peat = "\n".join(
        f'    <div class="step reveal r{k + 2}" style="left:{140 + k * 560}px"><img src="assets/{photo}" alt="{e(word)} peat">'
        f'<div class="word"><span>{k + 1}</span>{e(word)}</div><p>{e(words)}</p></div>'
        for k, (photo, word, words) in enumerate(PEAT))
    radar = "\n".join(
        f'    <p class="fact reveal r4" style="left:{140 + k * 560}px"><b>{e(name)}</b> {e(words)}</p>'
        for k, (name, words) in enumerate(RADAR))
    steps = "\n".join(
        f'    <div class="card reveal r2" style="left:{140 + k * 332}px"><div class="no">{k + 1}</div>'
        f'<div class="name">{e(name)}</div><p>{e(words)}</p></div>'
        for k, (name, words) in enumerate(STEPS))
    frames = "\n".join(
        f'    <div class="frame dark reveal r{2 + k // 2}" style="left:{140 + (k % 2) * 590}px; top:{232 + (k // 2) * 340}px; '
        f'width:570px; height:320px"><img src="assets/{gif}" alt="Recording of the app: {e(name)}"><span class="tag">{k + 1}</span></div>'
        for k, (gif, name, _) in enumerate(VIEWS))
    views = "\n".join(
        f'      <p><span class="tag">{k + 1}</span><b>{e(name)}</b> {e(words.format(o=ontology_words(counts)))}</p>'
        for k, (_, name, words) in enumerate(VIEWS))
    holds = "\n".join(f'      <p><b>{e(name)}</b> {e(words.format(**n))}</p>' for name, words in HOLDS)
    limits = "\n".join(f'      <p><b>{e(name)}</b>{e(words)}</p>' for name, words in LIMITS)
    plan = "\n".join(
        f'    <div class="when reveal r{2 + k}" style="left:{140 + k * 420}px"><i></i><div class="t">{e(when)}</div>'
        f'<div class="name">{e(name)}</div><p>{e(words)}</p></div>'
        for k, (when, name, words) in enumerate(NEXT))
    parts = {"peat": peat, "radar": radar, "steps": steps, "frames": frames, "views": views, "holds": holds,
             "limits": limits, "plan": plan, "lead": e(LEAD), "team": e(TEAM), "members": e(MEMBERS), "event": e(EVENT),
             "peat_sum": e(PEAT_SUM), "radar_title": e(RADAR_TITLE), "came_out": e(CAME_OUT), "app_url": APP_URL, "code_url": CODE_URL,
             "draft": '<div class="badge">draft: exploratory numbers</div>' if draft else ""}
    parts.update({f"source{k}": e(v) for k, v in SOURCES.items()})
    parts.update({k: e(v) for k, v in n.items()})
    for key, value in parts.items():
        out = out.replace("{{" + key + "}}", value)
    if "{{" in out:
        raise SystemExit("a slot was left unfilled: " + out[out.index("{{"):out.index("{{") + 40])
    return out


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dry Season Waltz</title>
<!-- Generated by submission/build_html_deck.py. Edit the script, not this file. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
/* ===========================================
   THEME: the app's control room. Ivory ink on dark; colour is kept for data.
   Sand = the radar echo fell, red = fire detected, blue = rain and the rise after it.
   =========================================== */
:root {
  --stage-bg: #05070a; --slide-bg: #0b0f14; --panel: #121822; --line: #23303e;
  --ink: #ece6d8; --dim: #8f9aa6; --sand: #e8c98e; --fire: #ff5a3c; --rain: #5aa9ee; --warn: #f2c14e;
  --sans: "IBM Plex Sans", sans-serif; --mono: "IBM Plex Mono", monospace;
  --ease: cubic-bezier(0.16, 1, 0.3, 1);
}
* { margin: 0; padding: 0; box-sizing: border-box; }

/* === FIXED 16:9 STAGE === */
html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; background: var(--stage-bg, #000); }
.deck-viewport { position: fixed; inset: 0; overflow: hidden; background: var(--stage-bg, #000); }
.deck-stage { position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; overflow: hidden; transform-origin: 0 0; background: var(--slide-bg, #fff); }
.slide { position: absolute; inset: 0; width: 1920px; height: 1080px; overflow: hidden; display: block; visibility: hidden; opacity: 0; pointer-events: none; background: var(--slide-bg, #fff); }
.slide.active, .slide.visible { visibility: visible; opacity: 1; pointer-events: auto; z-index: 1; }
img, video, canvas, svg { max-width: 100%; max-height: 100%; }
.deck-controls { position: fixed; left: 50%; bottom: 22px; transform: translateX(-50%); z-index: 1000; }
@media print { html, body { width: 1920px; height: auto; overflow: visible; background: #fff; } .deck-viewport { position: static; overflow: visible; background: #fff; } .deck-stage { position: static; width: auto; height: auto; transform: none !important; background: none; } .slide { position: relative; display: block !important; visibility: visible !important; opacity: 1 !important; pointer-events: auto !important; width: 1920px; height: 1080px; break-after: page; page-break-after: always; } .slide:last-child { break-after: auto; page-break-after: auto; } .deck-controls { display: none !important; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.2s !important; } }

/* ===========================================
   SHARED SLIDE PARTS: title, footer, draft badge, framed pictures
   =========================================== */
body { font-family: var(--sans); color: var(--ink); }
.slide { transition: opacity .5s ease; }
h2 { position: absolute; left: 140px; top: 96px; width: 1640px; font: 600 64px/1.12 var(--sans); letter-spacing: -0.02em; }
.rule { position: absolute; left: 140px; right: 140px; bottom: 112px; height: 1px; background: var(--line); }
.source { position: absolute; left: 140px; top: 990px; width: 1500px; font: 400 20px/1.3 var(--sans); color: var(--dim); }
.page { position: absolute; right: 140px; bottom: 62px; font: 400 20px var(--mono); color: var(--dim); }
.badge { position: absolute; right: 140px; top: 40px; padding: 6px 18px; border: 1px solid var(--warn); border-radius: 999px;
  font: 400 18px var(--mono); color: var(--warn); }
.frame { position: absolute; border: 1px solid var(--line); border-radius: 6px; overflow: hidden;
  box-shadow: 0 18px 50px rgba(0,0,0,.45); background: #fff; }
.frame img { display: block; width: 100%; height: 100%; object-fit: contain; }
.frame.dark { background: var(--slide-bg); }
.caption { position: absolute; font: 400 26px/1.45 var(--sans); color: var(--dim); }
.caption b { color: var(--ink); font-weight: 600; }
.caption .hh { color: var(--sand); }
a { color: var(--rain); text-decoration: none; border-bottom: 1px solid rgba(90,169,238,.45); }

/* ===========================================
   ENTRANCE: each slide's parts rise in order when it becomes the active slide
   =========================================== */
.reveal { opacity: 0; transform: translateY(24px); transition: opacity .7s var(--ease), transform .7s var(--ease); }
.slide.visible .reveal { opacity: 1; transform: none; }
.slide.visible .r1 { transition-delay: .05s } .slide.visible .r2 { transition-delay: .18s }
.slide.visible .r3 { transition-delay: .31s } .slide.visible .r4 { transition-delay: .44s }
.slide.visible .r5 { transition-delay: .57s }

/* ===========================================
   SLIDE 1: title over a photograph
   =========================================== */
.s1 .photo { position: absolute; right: 0; top: 0; width: 1240px; height: 1080px; object-fit: cover; object-position: 55% 40%;
  opacity: 0; transition: opacity 1.6s ease-out; }
.s1.visible .photo { opacity: 1; }
.s1 .veil { position: absolute; inset: 0; background: linear-gradient(90deg, #0b0f14 0%, #0b0f14 36%, rgba(11,15,20,.86) 50%, rgba(11,15,20,.25) 76%, rgba(11,15,20,.1) 100%); }
.s1 h1 { position: absolute; left: 140px; top: 210px; width: 900px; font: 600 132px/0.98 var(--sans); letter-spacing: -0.03em; }
.s1 .lead { position: absolute; left: 140px; top: 510px; width: 760px; font: 300 38px/1.38 var(--sans); }
.s1 .who { position: absolute; left: 140px; top: 760px; width: 800px; font: 400 26px/1.6 var(--sans); color: var(--dim); }
.s1 .who b { color: var(--ink); font-weight: 600; }

/* ===========================================
   SLIDE 2: how peat is degraded, one photograph a step
   =========================================== */
.step { position: absolute; top: 232px; width: 520px; }
.step img { display: block; width: 520px; height: 300px; object-fit: cover; border-radius: 6px; border: 1px solid var(--line); }
.step .word { margin-top: 22px; font: 600 36px var(--sans); }
.step .word span { display: inline-block; width: 44px; font: 500 26px var(--mono); color: var(--sand); }
.step p { margin-top: 10px; font: 400 25px/1.42 var(--sans); color: var(--dim); }
.sum { position: absolute; left: 140px; top: 806px; width: 1640px; padding-top: 24px; border-top: 1px solid var(--line);
  font: 400 28px/1.42 var(--sans); }

/* ===========================================
   SLIDE 3: three facts under the two pictures (its title takes two lines, so everything sits lower)
   =========================================== */
.fact { position: absolute; top: 756px; width: 520px; font: 400 25px/1.42 var(--sans); color: var(--dim); }
.fact b { display: block; margin-bottom: 4px; color: var(--ink); font: 600 28px/1.3 var(--sans); }

/* ===========================================
   SLIDE 4: the method as five cards, then what came out
   =========================================== */
.card { position: absolute; top: 224px; width: 312px; height: 312px; padding: 22px 24px; background: var(--panel);
  border: 1px solid var(--line); border-radius: 10px; }
.card .no { font: 500 24px var(--mono); color: var(--sand); }
.card .name { margin-top: 6px; font: 600 28px/1.2 var(--sans); }
.card p { margin-top: 10px; font: 400 21px/1.4 var(--sans); color: var(--dim); }
.tile { position: absolute; width: 283px; height: 176px; padding: 20px 22px; background: var(--panel);
  border: 1px solid var(--line); border-radius: 10px; }
.tile .num { font: 500 40px var(--mono); }
.tile .label { margin-top: 8px; font: 400 20px/1.35 var(--sans); color: var(--dim); }
.out { position: absolute; left: 891px; top: 768px; width: 889px; font: 400 26px/1.42 var(--sans); }

/* ===========================================
   SLIDE 5: four recordings of the app, numbered, with what each is for
   =========================================== */
.frame .tag, .do .tag { display: inline-block; width: 34px; height: 34px; border-radius: 50%; background: var(--ink); color: #0b0f14;
  font: 600 20px/34px var(--mono); text-align: center; }
.frame .tag { position: absolute; left: 12px; top: 12px; }
.do { position: absolute; left: 1350px; top: 232px; width: 430px; font: 400 24px/1.4 var(--sans); color: var(--dim); }
.do p { margin-bottom: 22px; } .do b { color: var(--ink); font-weight: 600; } .do .tag { margin-right: 12px; }
.do .go { margin-top: 30px; font-size: 28px; }

/* ===========================================
   SLIDE 6: what holds up, and what the map cannot say
   =========================================== */
.half { position: absolute; top: 224px; font: 400 25px/1.42 var(--sans); color: var(--dim); }
.half h3 { font: 600 34px var(--sans); color: var(--ink); margin-bottom: 20px; }
.half p { margin-bottom: 16px; } .half b { color: var(--ink); font-weight: 600; }
.cannot p { padding: 20px 0; margin: 0; border-top: 1px solid var(--line); font-size: 27px; }
.cannot b { display: block; font-size: 32px; margin-bottom: 4px; }

/* ===========================================
   SLIDE 7: the plan along a line, and the links
   =========================================== */
.track { position: absolute; left: 140px; right: 140px; top: 252px; height: 2px; background: var(--line); }
.when { position: absolute; top: 244px; width: 380px; }
.when i { display: block; width: 18px; height: 18px; border-radius: 50%; background: var(--sand); }
.when .t { margin-top: 24px; font: 500 22px var(--mono); color: var(--sand); }
.when .name { margin-top: 8px; font: 600 32px/1.2 var(--sans); }
.when p { margin-top: 12px; font: 400 24px/1.42 var(--sans); color: var(--dim); }
.links { position: absolute; left: 140px; top: 760px; font: 400 28px/1.8 var(--sans); color: var(--ink); }
.links b { display: inline-block; width: 230px; font-weight: 600; }
.by { position: absolute; left: 140px; top: 880px; font: 400 24px var(--sans); color: var(--dim); }

/* ===========================================
   PROGRESS (outside the stage)
   =========================================== */
.progress { position: fixed; left: 0; bottom: 0; height: 3px; background: var(--sand); transition: width .4s var(--ease); z-index: 1000; }
</style>
</head>
<body>
<div class="deck-viewport">
<main class="deck-stage" id="deckStage">

  <!-- 1. Title -->
  <section class="slide s1" aria-label="Slide 1: Dry Season Waltz">
    <img class="photo" src="assets/fire.jpg" alt="A firefighter hoses smouldering peat in a burnt forest">
    <div class="veil"></div>
    {{draft}}
    <h1 class="reveal r1">Dry Season Waltz</h1>
    <p class="lead reveal r2">{{lead}}</p>
    <p class="who reveal r3"><b>{{team}}</b><br>{{members}}<br>{{event}}</p>
    <div class="rule"></div>
    <p class="source">{{source1}}</p>
    <p class="page">01 / 07</p>
  </section>

  <!-- 2. The problem: how peat is degraded -->
  <section class="slide" aria-label="Slide 2: the problem">
    {{draft}}
    <h2 class="reveal r1">Peat does not burn until someone drains it</h2>
{{peat}}
    <p class="sum reveal r5">{{peat_sum}}</p>
    <div class="rule"></div>
    <p class="source">{{source2}}</p>
    <p class="page">02 / 07</p>
  </section>

  <!-- 3. What the radar is, and what it measures -->
  <section class="slide" aria-label="Slide 3: what the radar sees">
    {{draft}}
    <h2 class="reveal r1">{{radar_title}}</h2>
    <div class="frame reveal r2" style="left:140px; top:280px; width:800px; height:450px"><img src="assets/fig_cloud.png" alt="The same ground on 14 September 2026: smoke and cloud in VIIRS true colour, the land in NISAR L-band radar"></div>
    <div class="frame dark reveal r3" style="left:980px; top:280px; width:800px; height:450px"><img src="assets/explainer.gif" alt="Animated schematic of how the radar echo changes over wet and dry peat"></div>
{{radar}}
    <div class="rule"></div>
    <p class="source">{{source3}}</p>
    <p class="page">03 / 07</p>
  </section>

  <!-- 4. How it is done -->
  <section class="slide" aria-label="Slide 4: the method">
    {{draft}}
    <h2 class="reveal r1">How we turned radar passes into a map</h2>
{{steps}}
    <div class="frame reveal r3" style="left:140px; top:566px; width:711px; height:386px"><img src="assets/fig_season.png" alt="The season in one picture: the echo fading pass by pass on both orbits, forest flat, daily rain underneath"></div>
    <div class="tile reveal r4" style="left:891px; top:566px"><div class="num" style="color:var(--sand)">{{west_km2}}</div><div class="label">of peat in the west area where the echo fell on both orbits</div></div>
    <div class="tile reveal r4" style="left:1194px; top:566px"><div class="num" style="color:var(--sand)">{{east_km2}}</div><div class="label">the same, in the east area</div></div>
    <div class="tile reveal r4" style="left:1497px; top:566px"><div class="num" style="color:var(--rain)">{{rise}}</div><div class="label">back up on the first pass after the rain, {{rise_where}}</div></div>
    <p class="out reveal r5">{{came_out}}</p>
    <div class="rule"></div>
    <p class="source">{{source4}}</p>
    <p class="page">04 / 07</p>
  </section>

  <!-- 5. The app -->
  <section class="slide" aria-label="Slide 5: the app">
    {{draft}}
    <h2 class="reveal r1">The result is a map anyone can open</h2>
{{frames}}
    <div class="do reveal r4">
{{views}}
      <p class="go"><a href="{{app_url}}" target="_blank" rel="noopener">Open the map</a></p>
    </div>
    <div class="rule"></div>
    <p class="source">{{source5}}</p>
    <p class="page">05 / 07</p>
  </section>

  <!-- 6. How far to trust it -->
  <section class="slide" aria-label="Slide 6: how far to trust it">
    {{draft}}
    <h2 class="reveal r1">How far you can trust it</h2>
    <div class="half reveal r2" style="left:140px; width:800px">
      <h3>What holds up</h3>
    </div>
    <div class="frame reveal r2" style="left:140px; top:292px; width:720px; height:405px"><img src="assets/fig_orbits.png" alt="The dawn and the dusk orbit side by side, and compared square by square"></div>
    <div class="half reveal r3" style="left:140px; top:722px; width:800px">
{{holds}}
    </div>
    <div class="half cannot reveal r4" style="left:1010px; width:770px">
      <h3>What it cannot tell you</h3>
{{limits}}
    </div>
    <div class="rule"></div>
    <p class="source">{{source6}}</p>
    <p class="page">06 / 07</p>
  </section>

  <!-- 7. The plan -->
  <section class="slide" aria-label="Slide 7: what comes next">
    {{draft}}
    <h2 class="reveal r1">What comes next</h2>
    <div class="track"></div>
{{plan}}
    <div class="links reveal r5"><div><b>Open the map</b><a href="{{app_url}}" target="_blank" rel="noopener">{{app_url}}</a></div><div><b>Code and data</b><a href="{{code_url}}" target="_blank" rel="noopener">{{code_url}}</a></div></div>
    <p class="by reveal r5">{{team}}: {{members}}</p>
    <div class="rule"></div>
    <p class="source">{{source7}}</p>
    <p class="page">07 / 07</p>
  </section>

</main>
</div>
<div class="progress" id="progress"></div>

<script>
/* ===========================================
   SLIDE PRESENTATION CONTROLLER
   Arrow keys, Space, Page Up/Down, Home/End, mouse wheel and swipe move between slides.
   The address keeps the slide number (#3), so a link can open on a given slide.
   =========================================== */
class SlidePresentation {
  constructor() {
    this.slides = document.querySelectorAll('.slide');
    this.stage = document.getElementById('deckStage');
    this.bar = document.getElementById('progress');
    this.current = 0;
    this.lock = false;
    this.scale();
    addEventListener('resize', () => this.scale());
    this.keys(); this.wheel(); this.touch();
    const start = parseInt(location.hash.slice(1), 10);
    this.show(Number.isFinite(start) ? start - 1 : 0);
  }
  scale() {
    const f = Math.min(innerWidth / 1920, innerHeight / 1080);
    this.stage.style.transform = `translate(${(innerWidth - 1920 * f) / 2}px, ${(innerHeight - 1080 * f) / 2}px) scale(${f})`;
  }
  show(i) {
    this.current = Math.max(0, Math.min(i, this.slides.length - 1));
    this.slides.forEach((s, k) => { s.classList.toggle('active', k === this.current); s.classList.toggle('visible', k === this.current); });
    this.bar.style.width = `${((this.current + 1) / this.slides.length) * 100}%`;
    history.replaceState(null, '', `#${this.current + 1}`);
  }
  step(d) { if (this.lock) return; this.lock = true; this.show(this.current + d); setTimeout(() => this.lock = false, 450); }
  keys() {
    addEventListener('keydown', e => {
      if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(e.key)) { e.preventDefault(); this.step(1); }
      else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(e.key)) { e.preventDefault(); this.step(-1); }
      else if (e.key === 'Home') this.show(0);
      else if (e.key === 'End') this.show(this.slides.length - 1);
    });
  }
  wheel() { addEventListener('wheel', e => { if (Math.abs(e.deltaY) > 20) this.step(e.deltaY > 0 ? 1 : -1); }, { passive: true }); }
  touch() {
    let x0 = null;
    addEventListener('touchstart', e => { x0 = e.touches[0].clientX; }, { passive: true });
    addEventListener('touchend', e => { if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0; if (Math.abs(dx) > 40) this.step(dx < 0 ? 1 : -1); x0 = null; });
  }
}
new SlidePresentation();
</script>
</body>
</html>
"""


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--figures", default="submission/figures", type=Path)
    p.add_argument("--validation", default="app/public/validation.json", type=Path)
    p.add_argument("--ontology", default="pipeline/fusion/ontology.json", type=Path)
    p.add_argument("--photos", default="app/public/story", type=Path)
    p.add_argument("--out", default="submission/deck", type=Path)
    p.add_argument("--final", action="store_true", help="use only keys marked final, and drop the draft badge")
    a = p.parse_args()
    num = Numbers(a.validation, a.final)
    filled = page(numbers(num), draft=not a.final, counts=ontology_counts(a.ontology))
    copy_pictures(a.figures, a.photos, a.out / "assets")
    (a.out / "index.html").write_text(filled, encoding="utf-8")
    print(f"wrote {a.out / 'index.html'} ({'final' if a.final else 'draft'}); numbers from {len(set(num.used))} validation keys:")
    for k in sorted(set(num.used)):
        print(f"   {k} = {num.v[k]['value']} ({num.v[k].get('status')})")


if __name__ == "__main__":
    main()
