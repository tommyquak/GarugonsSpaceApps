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
PEAT_TITLE = "Peat burns far more easily once it is drained"
PEAT = [
    ("forest.jpg", "Wet", "A peat swamp is forest growing on metres of dead plants that never rotted, because the ground "
     "stays under water. It holds thousands of years of carbon, and while it stays wet it rarely burns."),
    ("canal.jpg", "Drained", "In the 1990s the Mega Rice Project dug some 4,600 km of canals to turn a million hectares "
     "of this swamp into rice fields. The scheme failed. The canals still drain the peat."),
    ("burnt.jpg", "Burnt", "Dry peat catches fire and smoulders under the surface for weeks. Indonesia's 2015 fires, many "
     "of them on peat, cost the country USD 16 billion, and the haze shut Singapore's schools."),
]
PEAT_SUM = ("This is peat degradation: drained, dried out, burnt, then burnt again. Indonesian law counts peat as damaged "
            "once the water sits more than 0.4 m below the surface. The hard part is seeing which ground is drying, "
            "because in the dry season it lies under cloud, and then under smoke.")
# Slide 3: what the radar is and what it measures.
RADAR_TITLE = "An optical satellite can't see past cloud and smoke, but radar can see the ground"
RADAR = [
    ("Same place, same day.", "14 September 2026. On the left, what an optical satellite saw: smoke and cloud. "
     "On the right, what NISAR saw: the land."),
    ("NISAR allows us to see beyond the smoke.", "Launched by NASA and ISRO in 2025, it sends out its own radio waves, "
     "24 cm long. They pass through cloud and smoke, by day or night, and it is built to return every 12 days."),
    ("The echo tells wet from dry.", "On open ground a wet surface sends back a strong echo and a dry one a weak echo. "
     "When open peat dries, the echo fades. Clearing fades it too, so we only ever say the echo fell."),
]
# Slide 4: how the map is made, one step a row, in the words we would use out loud.
STEPS_TITLE = "How we made the map, in five steps"
STEPS = [
    ("Get the radar pictures.", "NISAR flew over our two study areas about every 12 days from June to November 2026, "
     "once at dawn and once at dusk. We lined every picture up on the same 50 m grid."),
    ("Use the forest as a ruler.", "Thick forest looks the same to the radar all season. So we compare every spot with "
     "the forest near it, which cancels out the small differences between one picture and the next."),
    ("Find when the rain stopped.", "NASA's daily rainfall data gives the day the dry season began and the day the rain "
     "came back. A fixed rule reads the dates off, so we cannot pick ones that suit us."),
    ("Mark where the echo got weaker.", "We compare the start of the dry season with mid October. A spot is marked only "
     "if its echo got at least a fifth weaker (1 dB) in both the dawn and the dusk pictures."),
    ("See what came back with the rain.", "After the first rain, did the echo recover? We add where NASA detected fire "
     "and where the peat is, then sort every 1 km square into a group, by rules anyone can read."),
]
TILES = ["of peat in the west area where the echo got weaker", "the same, in the east area",
         "how much it came back on the first pass after the rain, {where}"]
IN_TERMS = ("In technical terms: NISAR L2 GCOV backscatter (L-band, HH and HV) from ascending track 125 and descending "
            "track 061, on a 50 m grid, each pass referenced to closed forest. A fall is 1 dB or more on both tracks. "
            "Classes are set per 1 km block by rules kept in one file, the ontology.")
CAME_OUT = ("In most places the echo came back after the first rain. In some it stayed weak, and we do not know why. "
            "Those are the places to check first.")
# Slide 5: the app. (recording, name, sentence); {o} is filled with the ontology counts.
VIEWS = [
    ("demo_season.gif", "Play the season.", "Watch the echo fade pass by pass, with NASA's fire detections building up beside it."),
    ("demo_check.gif", "See where to check.", "Every 1 km square of peat sorted into three levels, flat or in 3D. "
     "Download the list for a GPS."),
    ("demo_decide.gif", "Ask why.", "Each class has a written rule, open to read from the data to the answer. "
     "We call it the ontology: {o}."),
    ("demo_report.gif", "Print it.", "Three pages for a field team, ending in the squares to visit first."),
]
# Slide 6: how far to trust the map, in short, and what a restoration agency can do with it.
TRUST_TITLE = "How far to trust it, and what to do with it"
TRUST = [
    ("Two orbits agree.", "Looking from opposite sides, four days apart, they picked the same places "
     "(rank correlation {r_west} in the west, {r_east} in the east)."),
    ("It survived an attack.", "We asked an SI reviewer to break it. It found a start date just after rain. "
     "We fixed it, and the numbers got smaller."),
    ("It is not ground truth.", "Nobody has checked it in the field. It does not predict fire, and it covers "
     "one dry season in two areas."),
]
USE = [
    ("Take the list.", "Every 1 km square comes with its coordinates and the evidence behind it, in a file that opens "
     "in a GIS or on a GPS."),
    ("Visit the top of the list first.", "Start where the echo stayed weak after the rain, and where fire was detected. "
     "Measure the water depth and look at the canals."),
    ("The field team decides whether to act.", "Indonesia's peat agency restores by rewetting, replanting and supporting "
     "local livelihoods. Rewetting means blocking canals with dams, filling them in, and drilling deep wells."),
    ("Look again next season.", "NISAR is built to come back every 12 days. If the agency blocks a canal, it could use "
     "the same map next season to check how the radar echo changes there. We have not tested this."),
]
USE_SUM = "The map does not choose the remedy. It tells an agency where to look first."
# Slide 7: the plan. (when, what, sentence). The papers are in docs/REFERENCES.md.
NEXT = [
    ("Next dry season", "Check it on the ground", "About sixty visits with a field partner: water depth in a dipwell, "
     "canals and fire scars, at squares from each class. That calibrates the map, or shows where it is wrong."),
    ("Every season", "Run it again", "The code takes any area. A second and a third season will show how the method "
     "behaves in a wet year, and other peatlands can be added."),
    ("In two to three years", "Add subsidence measurement", "Drained peat sinks as it rots away. That sinking, called "
     "subsidence, is carbon lost to the air (Hooijer et al. 2012). L-band radar has measured it in Central Kalimantan "
     "(Tay et al. 2025). With enough NISAR passes we can test for it here."),
    ("Then", "Hand it over", "The list opens in any GIS or GPS. It needs an agency or a field group to take it up."),
]
SOURCES = {
    1: "Photo: putting out a peat fire, 2019. DenY Krisbiyantoro, Wikimedia Commons, CC BY-SA 4.0.",
    2: "Photos: Sugardiman / AusAID and Estey / AusAID (CC BY 2.0), Krisbiyantoro (CC BY-SA 4.0), Wikimedia Commons. "
       "Facts: Mongabay 2018, World Bank 2016, Regulation 57 of 2016.",
    3: "VIIRS Corrected Reflectance (NASA GIBS), NISAR L2 GCOV (NASA and ISRO, ASF DAAC). The animation is a schematic made with SI assistance.",
    4: "Figure: pipeline/figures.py. NISAR L2 GCOV (ASF DAAC), GPM IMERG (GES DISC), NASA FIRMS, PEATMAP (CC BY 4.0).",
    5: "Live app: tommyquak.github.io/GarugonsSpaceApps. Basemap: Sentinel-2 cloudless 2016 by EOX, CC BY 4.0.",
    6: "Figure: pipeline/figures.py. Audit: docs/AUDIT.md. Limits: docs/LIMITS.md. Restoration measures: Indonesia's peat and mangrove restoration agency (BRGM), as described by UN DESA.",
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
    """The figure as a smaller image for the deck: charts to a 256-colour PNG, figures with satellite pictures to JPEG.

    Keeps the deck small enough to upload to Google Drive in one call; the release files stay untouched."""
    if path.suffix.lower() == ".gif":
        return lit_first(path)               # animated: keep every frame
    img = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    if path.suffix.lower() in (".jpg", ".jpeg"):
        return str(path)
    img.thumbnail((1600, 1600))   # twice the widest a figure is shown, on a 1920 stage
    if path.stem in ("fig_map", "fig_cloud", "fig_orbits"):   # these hold satellite pictures, which PNG stores badly
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
    img.thumbnail((int(w * 1.3), int(h * 1.3)))   # a third more than the box, in stage pixels: sharp at full screen, and small
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=78, optimize=True)
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
            words(s, 140, 96, 1640, 160, heading, 64, bold=True, name="Title")
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
    s = new(2, PEAT_TITLE)
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
    s = new(3, RADAR_TITLE)   # two lines, so the pictures sit lower than on the other slides
    framed(s, fig / "fig_cloud.png", px(140), px(270), px(800), "Cloud against radar figure")
    framed(s, fig / "explainer.gif", px(980), px(270), px(800), "Radar explainer animation")
    for k, (name, sentence) in enumerate(RADAR):
        words(s, 140 + k * 560, 738, 520, 220, [[(name, {"bold": True, "color": INK, "size": 14})], sentence], 24,
              color=DIM, space_after=3)
    footer(s, 3, SOURCES[3], draft)
    s.notes_slide.notes_text_frame.text = "What NISAR is and what the echo means. Physics claims are the audited ones only."

    # 4. How it is done
    s = new(4, STEPS_TITLE)
    rows = [[(f"{k + 1}  ", {"color": SAND, "font": MONO, "bold": True}), (name + " ", {"bold": True, "color": INK}), sentence]
            for k, (name, sentence) in enumerate(STEPS)]
    words(s, 140, 232, 880, 620, rows, 24, color=DIM, space_after=11)
    words(s, 140, 876, 880, 84, IN_TERMS, 18, color=DIM)
    framed(s, fig / "fig_season.png", px(1080), px(232), px(700), "Season figure")   # 16:9, so 394 px tall
    rise, rise_where = rise_words(num)
    tiles = [(num.km2("fell_1db_km2_on_peat_west"), SAND), (num.km2("fell_1db_km2_on_peat_east"), SAND), (rise, RAIN)]
    for k, ((number, colour), label) in enumerate(zip(tiles, TILES)):
        x = 1080 + k * 240
        t = shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, px(x), px(650), px(220), px(170), PANEL, LINE)
        t.adjustments[0] = 0.06
        words(s, x + 18, 664, 190, 50, number, 32, color=colour, font=MONO, bold=True)
        words(s, x + 18, 716, 188, 100, label.format(where=rise_where), 17, color=DIM)
    words(s, 1080, 842, 700, 110, CAME_OUT, 23)
    footer(s, 4, SOURCES[4], draft)
    s.notes_slide.notes_text_frame.text = "How the map is made, in five plain steps, with the season in one figure and the three numbers that came out."

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

    # 6. How far to trust it, and what to do with it
    s = new(6, TRUST_TITLE)
    words(s, 140, 224, 760, 50, "How far you can trust it", 34, bold=True)
    framed(s, fig / "fig_orbits.png", px(140), px(286), px(480), "Orbits figure")
    n = {"r_west": f"{num.get('track5_west_orbit_spearman'):.2f}", "r_east": f"{num.get('track5_east_orbit_spearman'):.2f}"}
    words(s, 140, 578, 760, 380, [lead_in(name, sentence.format(**n)) for name, sentence in TRUST], 23, color=DIM,
          space_after=8)
    words(s, 980, 224, 800, 50, "What a restoration agency can do with it", 34, bold=True)
    rows = [[(f"{k + 1}  ", {"color": SAND, "font": MONO, "bold": True}), (name + " ", {"bold": True, "color": INK}), sentence]
            for k, (name, sentence) in enumerate(USE)]
    words(s, 980, 286, 800, 570, rows, 23, color=DIM, space_after=10)
    words(s, 980, 880, 800, 80, USE_SUM, 26)
    footer(s, 6, SOURCES[6], draft)
    s.notes_slide.notes_text_frame.text = ("Validity in short, then use: the list, the field visit, the agency's own restoration "
                                           "measures, and a second look next season. The map does not recommend an intervention.")

    # 7. The plan
    s = new(7, "What comes next")
    line(s, px(140), px(253), px(1780), px(253), LINE, 1.5)
    for k, (when, name, sentence) in enumerate(NEXT):
        x = 140 + k * 420
        shape(s, MSO_SHAPE.OVAL, px(x), px(244), px(18), px(18), SAND)
        words(s, x, 286, 380, 32, when, 22, color=SAND, font=MONO)
        # one box, so a name that takes two lines pushes its sentence down
        words(s, x, 322, 380, 380, [[(name, {"bold": True, "color": INK, "size": 15.5})], sentence], 23, color=DIM,
              space_after=5)
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
