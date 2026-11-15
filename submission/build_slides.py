# Written with Super Intelligence (SI) assistance.
"""Build the seven-slide demo deck (track 6) as a .pptx, ready to upload to Google Slides.

The order: title, the problem (how peat is degraded), what the radar sees, how the map is made, the app,
how far to trust it, what comes next. The words are the lists below; build_html_deck.py reads the same
lists. Every number of ours is read from validation.json; none is typed here. Outside facts carry their
source on the slide. The limits behind each claim are in docs/LIMITS.md.

    python submission/build_slides.py --figures submission/figures --out submission/deck.pptx
        # draft: exploratory numbers, tagged on every slide
    python submission/build_slides.py ... --final   # only keys marked final; stops if one is missing

The figures and the four app recordings come from the release: gh release download figures-v3 --dir submission/figures
The photographs are the ones of the app's opening story, in app/public/story, with their credits.
Both decks are laid out on a 1920 x 1080 stage, so a position here is the same number as in the web deck.
"""
import argparse
import io
import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

# A near-black ground, dark panels with hairline borders, light ink and a dim grey; colours keep their meaning from the app.
BG = RGBColor(0x0B, 0x0F, 0x14)
PANEL = RGBColor(0x12, 0x18, 0x22)
LINE = RGBColor(0x23, 0x30, 0x3E)
INK = RGBColor(0xE8, 0xED, 0xF2)
DIM = RGBColor(0x93, 0xA1, 0xB0)
SAND = RGBColor(0xE8, 0xC9, 0x8E)   # the fall in HH: sand to brown, as in the app
FIRE = RGBColor(0xFF, 0x5A, 0x3C)   # fire detections only
RAIN = RGBColor(0x5A, 0xA9, 0xEE)   # rain, and the rise after it
WARN = RGBColor(0xF2, 0xC1, 0x4E)   # the draft badge

FONT = "Archivo"
MONO = "JetBrains Mono"   # numbers only: they are measurements
W, H = Inches(13.333), Inches(7.5)
M = Inches(0.6)
# The words of the deck. build_html_deck.py reads the same lists, so the two decks cannot drift apart.
# Outside facts carry their source on the slide; our own numbers come from validation.json.
TEAM = "Team Garugons"
MEMBERS = "Tommy, Reagan, Gabriel, Kalent, Jan Hoe, Anson"
EVENT = "NASA Space Apps Challenge 2026 · Dancing with the SARs"
LEAD = ("What NASA's new radar saw on Borneo's peat through the 2026 dry season, "
        "while cloud and smoke hid it from every camera.")
# Slide 2: how peat is degraded, one photograph a step. (photo in app/public/story, word, sentence)
PEAT = [
    ("forest.jpg", "Wet", "A peat swamp is forest growing on metres of dead plants that never rotted, because the ground "
     "stays under water. It holds thousands of years of carbon, and wet peat does not burn."),
    ("canal.jpg", "Drained", "In the 1990s the Mega Rice Project dug some 4,600 km of canals to turn a million hectares "
     "of this swamp into rice fields. The rice failed. The canals still drain the peat."),
    ("burnt.jpg", "Burnt", "Dry peat catches fire and smoulders under the surface for weeks. Indonesia's 2015 fires, many "
     "of them on peat, cost the country USD 16 billion, and the haze shut Singapore's schools."),
]
PEAT_SUM = ("This is peat degradation: drained, dried out, burnt, then burnt again. Indonesian law counts peat as damaged "
            "once the water sits more than 0.4 m below the surface. The hard part is seeing which ground is drying, "
            "because in the dry season it lies under cloud, and then under smoke.")
# Slide 3: what the radar is and what it measures.
RADAR = [
    ("Same place, same day.", "14 September 2026. On the left, what a camera in orbit saw: smoke and cloud. "
     "On the right, what NISAR saw: the land."),
    ("It brings its own light.", "NISAR, launched by NASA and ISRO in 2025, sends out radio waves 24 cm long. They pass "
     "through cloud and smoke, by day or night, and the satellite is built to return every 12 days."),
    ("The echo tells wet from dry.", "On open ground a wet surface sends back a strong echo and a dry one a weak echo. "
     "When open peat dries, the echo fades. Clearing fades it too, so we only ever say the echo fell."),
]
# Slide 4: the method, one step a card.
STEPS = [
    ("Collect", "Every NISAR pass over two study areas, June to November 2026, from two orbits: one at dawn, one at dusk. "
     "All on one 50 m grid."),
    ("Steady", "Whole images shift a little between passes. Closed forest hardly changes, so we measure every pass "
     "against the forest nearby and the shift drops out."),
    ("Date the dry season", "NASA's daily rainfall record shows when the rain stopped and when it returned. A fixed rule "
     "picks the dates, not our eyes."),
    ("Measure the fall", "From the dry start to mid October, how much did the echo fade? A place counts only if both "
     "orbits saw it fade by 1 dB, about a fifth."),
    ("Wait for the rain", "Did the echo come back on the first pass after the rain? Add NASA's fire detections and a "
     "peat map, and each 1 km square gets a class by a written rule."),
]
CAME_OUT = ("On most of that land the echo rose again on the first pass after the rain. Where it stayed low we do not "
            "know why. Those are the places to check.")
# Slide 5: the app. (recording, name, sentence); {o} is filled with the ontology counts.
VIEWS = [
    ("demo_season.gif", "Play the season.", "Watch the echo fade pass by pass, with NASA's fire detections building up beside it."),
    ("demo_check.gif", "See where to check.", "Every 1 km square of peat sorted into three levels, flat or in 3D. "
     "Download the list for a GPS."),
    ("demo_decide.gif", "Ask why.", "Each class has a written rule, open to read from the data to the answer. "
     "We call it the ontology: {o}."),
    ("demo_report.gif", "Print it.", "Three pages for a field team, ending in the squares to visit first."),
]
# Slide 6: what holds up, and what the map cannot say.
HOLDS = [
    ("Two orbits picked the same places.", "They look from opposite sides, four days apart, and agree square by square "
     "(rank correlation {r_west} in the west area, {r_east} in the east)."),
    ("We asked a reviewer to break it.", "An SI reviewer found our first start date fell just after rain. We moved the "
     "start, the numbers got smaller, and the audit is published with the code."),
]
LIMITS = [
    ("Nobody has checked it on the ground.", "A weaker echo is not a measured water level."),
    ("It does not predict fire.", "We tested that, found nothing clear, and dropped the claim."),
    ("It is one dry season, in two areas.", "Both in Central Kalimantan. A wet year may look different."),
    ("It says where to look, not what to do.", "A square on the list is a place to visit, not a verdict."),
]
# Slide 7: the plan. (when, what, sentence). The papers are in docs/REFERENCES.md.
NEXT = [
    ("Next dry season", "Check it on the ground", "About sixty visits with a field partner: water depth in a dipwell, "
     "canals and fire scars, at squares from each class. That calibrates the map, or shows where it is wrong."),
    ("Every season", "Run it again", "The code takes any area. A second and a third season will show how the method "
     "behaves in a wet year, and other peatlands can be added."),
    ("In two to three years", "Add sinking ground", "Drained peat sinks as it rots away, which is carbon lost to the air "
     "(Hooijer et al. 2012). L-band radar has measured that in Central Kalimantan (Tay et al. 2025). With enough NISAR "
     "passes we can test for it here."),
    ("Then", "Hand it over", "The list opens in any GIS or GPS. It needs an agency or a field group to take it up."),
]
SOURCES = {
    1: "Photo: putting out a peat fire, 2019. DenY Krisbiyantoro, Wikimedia Commons, CC BY-SA 4.0.",
    2: "Photos: Sugardiman / AusAID and Estey / AusAID (CC BY 2.0), Krisbiyantoro (CC BY-SA 4.0), Wikimedia Commons. "
       "Facts: Mongabay 2018, World Bank 2016, Regulation 57 of 2016.",
    3: "VIIRS Corrected Reflectance (NASA GIBS), NISAR L2 GCOV (NASA and ISRO, ASF DAAC). The animation is a schematic made with SI assistance.",
    4: "Figure: pipeline/figures.py. NISAR L2 GCOV (ASF DAAC), GPM IMERG (GES DISC), NASA FIRMS, PEATMAP (CC BY 4.0).",
    5: "Live app: tommyquak.github.io/GarugonsSpaceApps. Basemap: Sentinel-2 cloudless 2016 by EOX, CC BY 4.0.",
    6: "Figure: pipeline/figures.py. Audit and response: docs/AUDIT.md. All limits: docs/LIMITS.md.",
    7: "Made with Super Intelligence (SI) assistance, from open NASA, ISRO and other data. Sources and licences: submission/LICENCES.md.",
}
APP_URL = "https://tommyquak.github.io/GarugonsSpaceApps/"
CODE_URL = "https://github.com/tommyquak/GarugonsSpaceApps"


class Numbers:
    """Reads values from validation.json and formats them; in --final mode only final entries pass."""

    def __init__(self, path, final):
        self.v = json.loads(Path(path).read_text())
        self.final = final
        self.used = []

    def get(self, key):
        if key not in self.v:
            raise SystemExit(f"{key} is not in validation.json")
        e = self.v[key]
        if self.final and e.get("status") != "final":
            raise SystemExit(f"{key} is not final yet (status {e.get('status')})")
        self.used.append(key)
        return e["value"]

    def km2(self, key):
        return f"{self.get(key):,.0f} km²"

    def share(self, key):
        return f"{self.get(key) * 100:.0f}%"

    def db(self, key, sign=True):
        x = self.get(key)
        return f"{x:+.1f} dB" if sign else f"{abs(x):.1f} dB"


def ontology_counts(path):
    """How many sources, observations, states and classes the ontology file holds, as words for a sentence."""
    o = json.loads(Path(path).read_text())
    counts = {k: str(len(o[k])) for k in ("sources", "observations", "states")}
    counts["classes"] = str(sum(1 for a in o["actions"] if a.get("id") != "none"))   # "no class" is not a class
    return counts


def ontology_words(counts):
    """The ontology's size as words for a sentence."""
    return (f"{counts['sources']} sources, {counts['observations']} observations, {counts['states']} states "
            f"and {counts['classes']} classes")


def rise_words(num):
    """The median rise on the first pass after the rain in the west area, and which orbits it holds for."""
    dawn, dusk = num.db("recovery_hh_median_rebound_west_125"), num.db("recovery_hh_median_rebound_west_061")
    return (dawn, "on both orbits") if dawn == dusk else (f"{dawn} / {dusk}", "dawn / dusk orbit")


def text(slide, x, y, w, h, runs, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space_after=0, name=None, font=None):
    """A text box. runs is a string, or a list of paragraphs, each a string or a list of (text, options) runs."""
    box = slide.shapes.add_textbox(x, y, w, h)
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        for chunk in (para if isinstance(para, list) else [(para, {})]):
            t, o = chunk if isinstance(chunk, tuple) else (chunk, {})
            r = p.add_run()
            r.text = t
            f = r.font
            f.name = o.get("font", font or FONT)
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.color.rgb = o.get("color", color)
            if "link" in o:
                r.hyperlink.address = o["link"]
    return box


def background(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def compact(path):
    """The figure as a smaller image for the deck: charts to a 256-colour PNG, the photographic map to JPEG.

    Keeps the deck small enough to upload to Google Drive in one call; the release files stay untouched."""
    if path.suffix.lower() == ".gif":
        return lit_first(path)               # animated: keep every frame
    img = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    if path.suffix.lower() in (".jpg", ".jpeg"):
        return str(path)
    if path.stem == "fig_map":
        img.save(buf, "JPEG", quality=86, optimize=True)
    else:
        img.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf


def lit_first(path):
    """The GIF reordered to start at its first lit frame, so stills and thumbnails of the slide are not black.

    A GIF that already starts lit is passed through untouched."""
    from PIL import ImageSequence, ImageStat
    im = Image.open(path)
    frames = [f.convert("RGB") for f in ImageSequence.Iterator(im)]
    durations = []
    for i in range(len(frames)):
        im.seek(i)
        durations.append(im.info.get("duration", 80))
    light = [sum(ImageStat.Stat(f).mean) / 3 for f in frames]
    start = next(i for i, v in enumerate(light) if v >= 0.6 * max(light))
    if start == 0:
        return str(path)
    order = list(range(start, len(frames))) + list(range(start))
    buf = io.BytesIO()
    frames[order[0]].save(buf, "GIF", save_all=True, append_images=[frames[i] for i in order[1:]],
                          duration=[durations[i] for i in order], loop=0, optimize=False)
    buf.seek(0)
    return buf


def picture(slide, path, x, y, w=None, h=None, name=None):
    pic = slide.shapes.add_picture(compact(path), x, y, w, h)
    if name:
        pic.name = name
    return pic


def title(slide, words):
    text(slide, M, Inches(0.45), W - 2 * M, Inches(1.0), words, size=30, bold=True, color=INK,
         anchor=MSO_ANCHOR.TOP, name="Title")


def footer(slide, n, source, draft):
    line(slide, M, H - Inches(0.62), W - M, H - Inches(0.62), LINE, 0.75)
    text(slide, M, H - Inches(0.5), Inches(11.0), Inches(0.4), source, size=10, color=DIM, name="Source")
    text(slide, W - M - Inches(1.2), H - Inches(0.5), Inches(1.2), Inches(0.3), f"{n:02d} / 07",
         size=10, color=DIM, align=PP_ALIGN.RIGHT, name="Page", font=MONO)
    if draft:
        badge = shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, W - M - Inches(2.75), Inches(0.12), Inches(2.75), Inches(0.28),
                      BG, WARN)
        badge.adjustments[0] = 0.5
        badge.name = "Draft badge"
        text(slide, W - M - Inches(2.75), Inches(0.15), Inches(2.75), Inches(0.22), "draft: exploratory numbers",
             size=9, color=WARN, align=PP_ALIGN.CENTER, font=MONO)


def framed(slide, path, x, y, w, name):
    """A picture with a hairline frame, like a screen on the wall."""
    pic = picture(slide, path, x, y, w=w, name=name)
    pic.line.color.rgb = LINE
    pic.line.width = Pt(0.75)
    return pic


def line(slide, x1, y1, x2, y2, color, width=2.0, arrow=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    c.line.color.rgb = color
    c.line.width = Pt(width)
    if arrow:
        ln = c.line._get_or_add_ln()
        tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
        ln.append(tail)
    return c


def shape(slide, kind, x, y, w, h, fill, line_color=None):
    s = slide.shapes.add_shape(kind, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line_color is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line_color
    s.shadow.inherit = False
    return s


def link_colour(prs, hex6):
    """Hyperlinks take the theme's link colour, not the run's: set it to one that reads on white and on ink."""
    from lxml import etree
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    theme = prs.slide_masters[0].part.part_related_by(RT.THEME)
    root = etree.fromstring(theme.blob)
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    for tag in ("hlink", "folHlink"):
        el = root.find(f".//a:clrScheme/a:{tag}", ns)
        for child in list(el):
            el.remove(child)
        etree.SubElement(el, qn("a:srgbClr"), val=hex6)
    theme._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def px(n):
    """Stage pixels to slide units: both decks are laid out on a 1920 x 1080 stage, and the slide is 13.333 in wide."""
    return Emu(int(n * 914400 / 144))


def photo(slide, path, x, y, w, h, name, focus=(0.5, 0.5)):
    """A photograph cropped to fill a box of w by h stage pixels, keeping the part around focus."""
    img = Image.open(path).convert("RGB")
    want = w / h
    if img.width / img.height > want:
        cw = int(img.height * want)
        left = int((img.width - cw) * focus[0])
        img = img.crop((left, 0, left + cw, img.height))
    else:
        ch = int(img.width / want)
        top = int((img.height - ch) * focus[1])
        img = img.crop((0, top, img.width, top + ch))
    img.thumbnail((1400, 1400))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=84, optimize=True)
    buf.seek(0)
    pic = slide.shapes.add_picture(buf, px(x), px(y), px(w), px(h))
    pic.name = name
    return pic


def words(slide, x, y, w, h, runs, size, **kw):
    """text() in stage pixels; a size in pixels is half as many points."""
    return text(slide, px(x), px(y), px(w), px(h), runs, size=size / 2, **kw)


def lead_in(name, rest, size=None):
    """A paragraph that opens with a few bold words in ink and goes on in the dim colour."""
    o = {"bold": True, "color": INK}
    if size:
        o["size"] = size / 2
    return [(name + " ", o), rest]


def build(a):
    num = Numbers(a.validation, a.final)
    draft = not a.final
    fig, story = Path(a.figures), Path(a.photos)
    counts = ontology_counts(a.ontology)
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    blank = prs.slide_layouts[6]

    def new(n, heading=None):
        s = prs.slides.add_slide(blank)
        background(s, BG)
        if heading:
            words(s, 140, 96, 1640, 90, heading, 64, bold=True, name="Title")
        return s

    # 1. Title
    s = new(1)
    photo(s, story / "fire.jpg", 880, 0, 1040, 968, "Photograph: putting out a peat fire", focus=(0.85, 0.4))
    words(s, 140, 200, 720, 290, "Dry Season Waltz", 124, bold=True)
    words(s, 140, 510, 700, 220, LEAD, 36)
    words(s, 140, 770, 700, 150, [[(TEAM, {"bold": True, "color": INK})], MEMBERS, EVENT], 25, color=DIM, space_after=4)
    footer(s, 1, SOURCES[1], draft)
    s.notes_slide.notes_text_frame.text = "Title: what the project is, who made it, which challenge."

    # 2. The problem: how peat is degraded
    s = new(2, "Peat does not burn until someone drains it")
    for k, (name, word, sentence) in enumerate(PEAT):
        x = 140 + k * 560
        photo(s, story / name, x, 232, 520, 300, f"Photograph: {word.lower()} peat")
        words(s, x, 550, 520, 50, [[(f"{k + 1}  ", {"color": SAND, "font": MONO, "size": 13}), (word, {"bold": True})]], 36)
        words(s, x, 610, 520, 190, sentence, 24, color=DIM)
    line(s, px(140), px(806), px(1780), px(806), LINE, 0.75)
    words(s, 140, 826, 1640, 130, PEAT_SUM, 27)
    footer(s, 2, SOURCES[2], draft)
    s.notes_slide.notes_text_frame.text = "The problem: what peat is, how it is degraded, what it costs, and why nobody can watch it in the dry season."

    # 3. What the radar is, and what it measures
    s = new(3, "A camera sees the smoke. Radar sees the ground")
    framed(s, fig / "fig_cloud.png", px(140), px(232), px(800), "Cloud against radar figure")
    framed(s, fig / "explainer.gif", px(980), px(232), px(800), "Radar explainer animation")
    for k, (name, sentence) in enumerate(RADAR):
        words(s, 140 + k * 560, 716, 520, 230, [[(name, {"bold": True, "color": INK, "size": 14})], sentence], 24,
              color=DIM, space_after=3)
    footer(s, 3, SOURCES[3], draft)
    s.notes_slide.notes_text_frame.text = "What NISAR is and what the echo means. Physics claims are the audited ones only."

    # 4. How it is done
    s = new(4, "How we turned radar passes into a map")
    for k, (name, sentence) in enumerate(STEPS):
        x = 140 + k * 332
        card = shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, px(x), px(224), px(312), px(312), PANEL, LINE)
        card.adjustments[0] = 0.04
        words(s, x + 24, 244, 264, 34, str(k + 1), 24, color=SAND, font=MONO)
        words(s, x + 24, 282, 264, 40, name, 27, bold=True)
        words(s, x + 24, 330, 268, 200, sentence, 20, color=DIM)
    framed(s, fig / "fig_season.png", px(140), px(566), px(686), "Season figure")   # 16:9, so 386 px tall
    rise, rise_where = rise_words(num)
    tiles = [(num.km2("fell_1db_km2_on_peat_west"), "of peat in the west area where the echo fell on both orbits", SAND),
             (num.km2("fell_1db_km2_on_peat_east"), "the same, in the east area", SAND),
             (rise, f"back up on the first pass after the rain, {rise_where}", RAIN)]
    for k, (number, label, colour) in enumerate(tiles):
        x = 891 + k * 303
        t = shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, px(x), px(566), px(283), px(176), PANEL, LINE)
        t.adjustments[0] = 0.06
        words(s, x + 22, 584, 245, 56, number, 38, color=colour, font=MONO, bold=True)
        words(s, x + 22, 648, 245, 90, label, 19, color=DIM)
    words(s, 891, 772, 889, 150, CAME_OUT, 25)
    footer(s, 4, SOURCES[4], draft)
    s.notes_slide.notes_text_frame.text = "The method in five steps, the season in one figure, and the three numbers that came out."

    # 5. The app
    s = new(5, "The result is a map anyone can open")
    items = []
    for k, (gif, name, sentence) in enumerate(VIEWS):
        x, y = 140 + (k % 2) * 590, 232 + (k // 2) * 340
        framed(s, fig / gif, px(x), px(y), px(570), f"Recording: {name}")
        dot = shape(s, MSO_SHAPE.OVAL, px(x + 12), px(y + 12), px(34), px(34), INK)
        dot.name = f"Number {k + 1}"
        words(s, x + 12, y + 16, 34, 26, str(k + 1), 20, color=BG, bold=True, align=PP_ALIGN.CENTER, font=MONO)
        items.append([(f"{k + 1}  ", {"color": SAND, "font": MONO, "bold": True}), (name + " ", {"bold": True, "color": INK}),
                      sentence.format(o=ontology_words(counts))])
    items.append([("Open the map", {"bold": True, "link": APP_URL, "size": 14})])
    words(s, 1350, 232, 430, 700, items, 23, color=DIM, space_after=11)
    footer(s, 5, SOURCES[5], draft)
    s.notes_slide.notes_text_frame.text = ("Four recordings of the live app (figures-v3): the season, Where to check tilting "
                                           "into 3D, the ontology under How it decides, and the field assessment.")

    # 6. How far to trust it
    s = new(6, "How far you can trust it")
    words(s, 140, 224, 800, 50, "What holds up", 34, bold=True)
    framed(s, fig / "fig_orbits.png", px(140), px(292), px(720), "Orbits figure")
    n = {"r_west": f"{num.get('track5_west_orbit_spearman'):.2f}", "r_east": f"{num.get('track5_east_orbit_spearman'):.2f}"}
    words(s, 140, 722, 800, 240, [lead_in(name, sentence.format(**n)) for name, sentence in HOLDS], 24, color=DIM,
          space_after=8)
    words(s, 1010, 224, 770, 50, "What it cannot tell you", 34, bold=True)
    for k, (name, sentence) in enumerate(LIMITS):
        y = 292 + k * 150
        line(s, px(1010), px(y), px(1780), px(y), LINE, 0.75)
        words(s, 1010, y + 24, 770, 46, name, 31, bold=True)
        words(s, 1010, y + 72, 770, 60, sentence, 26, color=DIM)
    footer(s, 6, SOURCES[6], draft)
    s.notes_slide.notes_text_frame.text = "Validity: two independent orbits and the audit; then the limits, plainly."

    # 7. The plan
    s = new(7, "What comes next")
    line(s, px(140), px(253), px(1780), px(253), LINE, 1.5)
    for k, (when, name, sentence) in enumerate(NEXT):
        x = 140 + k * 420
        shape(s, MSO_SHAPE.OVAL, px(x), px(244), px(18), px(18), SAND)
        words(s, x, 286, 380, 32, when, 22, color=SAND, font=MONO)
        words(s, x, 322, 380, 46, name, 31, bold=True)
        words(s, x, 374, 380, 300, sentence, 23, color=DIM)
    links = [
        [("Open the map   ", {"bold": True, "color": INK}), (APP_URL, {"link": APP_URL})],
        [("Code and data   ", {"bold": True, "color": INK}), (CODE_URL, {"link": CODE_URL})],
    ]
    words(s, 140, 760, 1640, 110, links, 27, color=DIM, space_after=6)
    words(s, 140, 880, 1640, 40, f"{TEAM}: {MEMBERS}", 24, color=DIM)
    footer(s, 7, SOURCES[7], draft)
    s.notes_slide.notes_text_frame.text = ("The plan, in order. Subsidence is a plan, not a result: one season is too short "
                                           "to show it, and nothing in this deck measures it.")

    link_colour(prs, "5AA9EE")
    prs.save(a.out)
    print(f"wrote {a.out} ({'final' if a.final else 'draft'}); numbers from {len(set(num.used))} validation keys:")
    for k in sorted(set(num.used)):
        print(f"   {k} = {num.v[k]['value']} ({num.v[k].get('status')})")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--figures", default="submission/figures", type=Path)
    p.add_argument("--validation", default="app/public/validation.json", type=Path)
    p.add_argument("--ontology", default="pipeline/fusion/ontology.json", type=Path)
    p.add_argument("--photos", default="app/public/story", type=Path)
    p.add_argument("--out", default="submission/deck.pptx", type=Path)
    p.add_argument("--final", action="store_true", help="use only keys marked final, and drop the draft tag")
    build(p.parse_args())
