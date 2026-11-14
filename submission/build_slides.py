# Written with Super Intelligence (SI) assistance.
"""Build the seven-slide demo deck (track 6) as a .pptx, ready to upload to Google Slides.

Every number on a slide is read from validation.json; none is typed here. The order is the
one agreed on issue #36: the problem, what NISAR sees, the season, the app, why believe it,
what we do not see, what comes next. Claims stay inside docs/AUDIT.md "What we can still claim".

    python submission/build_slides.py --figures submission/figures --validation pipeline/out/validation.json \\
        --out submission/deck.pptx            # draft: exploratory numbers, tagged on every slide
    python submission/build_slides.py ... --final   # only keys marked final; stops if one is missing

Figures, the four app GIFs and app_room.jpg (the app's entry view) come from the release:
gh release download figures-v3 --dir submission/figures
Slide 3 gives the reasons behind the method and slide 4 the app's four views; the counts of the
ontology on slide 4 are read from pipeline/fusion/ontology.json, not typed.
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
# The choices behind the method, each with its reason (slide 3). build_html_deck.py uses the same list.
CHOICES = [
    ("Forest as the yardstick.", "Each pass is measured against closed forest, which removes shifts that affect a whole scene."),
    ("Two orbits must agree.", "Dawn and dusk look from opposite sides; a fall counts only where both see it."),
    ("The dry window comes from rainfall.", "Its start and end are set from the daily rain record by a fixed rule, not by eye."),
    ("Wait for the first rain.", "What comes back with the rain was moisture; what stays low is where to look."),
    ("Levels, not the size of the fall.", "Peat beside a canal falls far and recovers, so blocks are ranked by lasting change."),
    ("One ontology.", "Sources, observations, states and classes, with their thresholds, live in one file that the pipeline and the app both read."),
]
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
    return {k: str(len(o[k])) for k in ("sources", "observations", "states", "actions")}


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
    text(slide, M, H - Inches(0.5), Inches(10.5), Inches(0.3), source, size=10, color=DIM, name="Source")
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


def tile(slide, x, y, w, h, number, label, colour, small=False):
    """A panel with a measured number over a short label; small is the size for a row of three under a figure."""
    t = shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, PANEL, LINE)
    t.adjustments[0] = 0.08
    pad, top, below = (Inches(0.14), Inches(0.1), Inches(0.46)) if small else (Inches(0.18), Inches(0.15), Inches(0.62))
    text(slide, x + pad, y + top, w - 2 * pad, Inches(0.4), number, size=17 if small else 22, color=colour,
         font=MONO, bold=True)
    text(slide, x + pad, y + below, w - 2 * pad, h - below - Inches(0.06), label, size=10 if small else 12, color=DIM)


def limits_table(slide, x, y, w, rows):
    """Limit | Our answer, with hairlines under each row and no fills."""
    t = slide.shapes.add_table(len(rows) + 1, 2, x, y, w, Inches(0.4) * (len(rows) + 1)).table
    t.columns[0].width = int(w * 0.42)
    t.columns[1].width = w - int(w * 0.42)
    tbl = t._tbl
    tbl.tblPr.set("firstRow", "0")
    tbl.tblPr.set("bandRow", "0")
    style = tbl.tblPr.find(qn("a:tableStyleId"))
    if style is None:
        style = tbl.tblPr.makeelement(qn("a:tableStyleId"), {})
        tbl.tblPr.append(style)
    style.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"   # built-in "No Style, No Grid"
    for r, row in enumerate([("Limit", "Our answer")] + rows):
        for c, content in enumerate(row):
            cell = t.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = BG
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.12)
            cell.margin_top = cell.margin_bottom = Inches(0.07)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            runs = [(content.upper(), {"bold": True, "color": DIM, "size": 10})] if r == 0 else (
                content if isinstance(content, list) else [(content, {})])
            for t_, o in runs:
                run = p.add_run()
                run.text = t_
                run.font.name = FONT
                run.font.size = Pt(o.get("size", 13))
                run.font.bold = o.get("bold", False)
                run.font.color.rgb = o.get("color", INK)
            tcPr = cell._tc.get_or_add_tcPr()
            for k, edge in enumerate(("a:lnL", "a:lnR", "a:lnT", "a:lnB")):   # borders come before the fill
                ln = tcPr.makeelement(qn(edge), {"w": "9525" if edge == "a:lnB" else "0"})
                if edge == "a:lnB":
                    fill = ln.makeelement(qn("a:solidFill"), {})
                    fill.append(fill.makeelement(qn("a:srgbClr"), {"val": "23303E"}))
                else:
                    fill = ln.makeelement(qn("a:noFill"), {})
                ln.append(fill)
                tcPr.insert(k, ln)
    return t


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


def build(a):
    num = Numbers(a.validation, a.final)
    draft = not a.final
    fig = Path(a.figures)
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    blank = prs.slide_layouts[6]

    # 1. The problem, and the takeaway
    s = prs.slides.add_slide(blank)
    background(s, BG)
    framed(s, fig / "fig_map.png", Inches(6.55), Inches(1.6), Inches(6.2), "One-look map")   # 1617 x 1032 px
    text(s, M, Inches(0.9), Inches(5.6), Inches(1.0), "Dry Season Waltz", size=44, bold=True, color=INK)
    text(s, M, Inches(1.95), Inches(5.6), Inches(2.2),
         "NISAR lets anyone watch a peat dry season through cloud and smoke: an open map of where the radar "
         "echo fell, where fire was detected and what changed with the rain, with its evidence and its limits attached.",
         size=17, color=INK)
    text(s, M, Inches(4.0), Inches(5.6), Inches(1.6),
         "Every dry season, drained peat in Borneo is at its most flammable, some of it burns, and the haze reaches "
         "cities across the region. Cloud, then smoke, hides the ground from optical satellites just then.",
         size=14, color=DIM)
    text(s, M, Inches(6.05), Inches(5.6), Inches(0.3), "Team Garugons · NASA Space Apps 2026 · Dancing with the SARs",
         size=12, color=DIM)
    footer(s, 1, "Map: where HH fell by 1 dB or more, mid July to mid October 2026, with the PEATMAP outline.", draft)
    s.notes_slide.notes_text_frame.text = "The problem and the one takeaway."

    # 2. What NISAR sees: the problem in one picture, and how the radar gets through
    s = prs.slides.add_slide(blank)
    background(s, BG)
    title(s, "Cloud and smoke hide the ground from optical satellites. NISAR's radar sees through them")
    framed(s, fig / "fig_cloud.png", M, Inches(1.6), Inches(5.95), "Cloud against radar figure")
    framed(s, fig / "explainer.gif", Inches(6.78), Inches(1.6), Inches(5.95), "Radar explainer animation")
    text(s, M, Inches(5.1), Inches(5.95), Inches(1.5),
         [[("Every 12 days, day or night. ", {"bold": True, "color": INK}),
           "The same ground on the same day: smoke and cloud for the optical satellite, the land for the radar."]],
         size=14, color=DIM)
    text(s, Inches(6.78), Inches(5.1), Inches(5.95), Inches(1.5),
         [[("HH. ", {"bold": True, "color": SAND}),
           "A wetter surface sends back a stronger echo: as open peat dries, HH falls. Closed forest barely changed, "
           "so it is the yardstick. "], [("HV ", {"bold": True, "color": INK}),
           "comes mostly from woody vegetation, but responds to moisture too. A schematic, not data."]],
         size=14, color=DIM, space_after=4)
    footer(s, 2, "VIIRS Corrected Reflectance (NASA GIBS), NISAR L2 GCOV (ASF DAAC). Animation made with SI assistance.", draft)
    s.notes_slide.notes_text_frame.text = "The problem in one picture, and how the radar sees the ground. Physics claims are the audited ones only."

    # 3. The season in one picture
    s = prs.slides.add_slide(blank)
    background(s, BG)
    title(s, "On open peat HH fell through the dry season, then rose with the first rain. Six choices make that hold")
    fw = Inches(6.9)
    framed(s, fig / "fig_season.png", M, Inches(1.65), fw, "Season figure")   # 16:9, so 3.88 in tall
    dawn, dusk = num.db("recovery_hh_median_rebound_west_125"), num.db("recovery_hh_median_rebound_west_061")
    rise, rise_where = (dawn, "on both orbits") if dawn == dusk else (f"{dawn} / {dusk}", "dawn / dusk orbit")
    gap = Inches(0.15)
    ty, tw, th = Inches(5.68), int((fw - 2 * gap) / 3), Inches(1.08)
    tile(s, M, ty, tw, th, num.km2("fell_1db_km2_on_peat_west"),
         "of mapped peat in the west box fell 1 dB or more, on both orbits", SAND, small=True)
    tile(s, M + tw + gap, ty, tw, th, num.km2("fell_1db_km2_on_peat_east"), "the same, in the east box", SAND, small=True)
    tile(s, M + 2 * (tw + gap), ty, tw, th, rise,
         f"rise on the first pass after rain, {rise_where}; none before it", RAIN, small=True)
    why = [[(name + " ", {"bold": True, "color": INK}), reason] for name, reason in CHOICES]
    text(s, Inches(7.85), Inches(1.6), Inches(4.88), Inches(5.2), why, size=13, color=DIM, space_after=9)
    footer(s, 3, "Figure: pipeline/figures.py. NISAR L2 GCOV (ASF DAAC), GPM IMERG (GES DISC), PEATMAP (CC BY 4.0).", draft)
    s.notes_slide.notes_text_frame.text = ("The season at a glance: the fall, deep forest flat as the yardstick, daily rain underneath. "
                                           "Beside it, the six choices behind the method and the reason for each.")

    # 4. The app
    s = prs.slides.add_slide(blank)
    background(s, BG)
    title(s, "An open map with four views: play the season, see where to check, read the rule, print the list")
    gw, gap = Inches(4.4), Inches(0.15)   # the four recordings in a grid of two by two, each 16:9
    gh = int(gw * 9 / 16)
    views = [("demo_season.gif", "Season demo"), ("demo_check.gif", "Where to check demo"),
             ("demo_decide.gif", "How it decides demo"), ("demo_report.gif", "Field assessment demo")]
    for k, (name, label) in enumerate(views):
        framed(s, fig / name, M + (k % 2) * (gw + gap), Inches(1.65) + (k // 2) * (gh + gap), gw, label)
    o = ontology_counts(a.ontology)
    items = [
        [("The season. ", {"bold": True, "color": INK}), "Every pass on both orbits; fire builds up beside the fall."],
        [("Where to check. ", {"bold": True, "color": INK}),
         "1 km blocks in three levels, flat or in 3D, ranked, as CSV or GeoJSON."],
        [("How it decides. ", {"bold": True, "color": INK}),
         f"The ontology, drawn from its file: {o['sources']} sources, {o['observations']} observations, {o['states']} states "
         f"and {o['actions']} classes, each rule open to read."],
        [("Field assessment. ", {"bold": True, "color": INK}), "Three pages to print, ending in the blocks to visit first."],
        [("Open the map", {"bold": True, "link": APP_URL})],
    ]
    tx = M + 2 * gw + gap + Inches(0.3)
    text(s, tx, Inches(1.65), W - M - tx, Inches(5.1), items, size=13, color=DIM, space_after=10)
    footer(s, 4, "Live app: tommyquak.github.io/GarugonsSpaceApps. Basemap: Sentinel-2 cloudless 2016 by EOX, CC BY 4.0.", draft)
    s.notes_slide.notes_text_frame.text = ("Four recordings of the live app (figures-v3), left to right, top to bottom: the season, "
                                           "Where to check tilting into 3D, the ontology under How it decides, and the field assessment.")

    # 5. Why believe it
    s = prs.slides.add_slide(blank)
    background(s, BG)
    title(s, "Why believe it: two orbits agree, and an audit we asked for made the answer smaller")
    framed(s, fig / "fig_orbits.png", M, Inches(1.7), Inches(5.95), "Orbits figure")
    framed(s, fig / "fig_start.png", Inches(6.78), Inches(1.7), Inches(5.95), "Start figure")
    text(s, M, Inches(5.2), Inches(5.95), Inches(1.4),
         [[("Two orbits, one answer. ", {"bold": True, "color": INK}),
           f"Dawn and dusk look from opposite sides, hours apart, and agree block by block: Spearman r = "
           f"{num.get('track5_west_orbit_spearman'):.2f} in the west box, {num.get('track5_east_orbit_spearman'):.2f} "
           f"in the east (the scatter shows Pearson r)."]], size=14, color=DIM)
    text(s, Inches(6.78), Inches(5.2), Inches(5.95), Inches(1.4),
         [[("Audited half way. ", {"bold": True, "color": INK}),
           "An independent audit found our first start date came just after rain. We now start from the first "
           "rain-free passes, and published the audit with our response."]], size=14, color=DIM)
    footer(s, 5, "Figures: pipeline/figures.py. Audit and response: docs/AUDIT.md.", draft)
    s.notes_slide.notes_text_frame.text = "Validity: independent orbits, and the audit as evidence, not as the headline."

    # 6. The honest limits, with our answers
    s = prs.slides.add_slide(blank)
    background(s, BG)
    title(s, "What the radar cannot tell us yet, and our answers")
    limits_table(s, M, Inches(1.6), Inches(7.45), [
        ([("Not checked on the ground. ", {"bold": True}), ("A fall in HH is not a measured water table.", {})],
         "A rainfall model from a published gauge record bridges the gap (right), as support only. About sixty "
         "dipwell visits would calibrate the map or prove it wrong."),
        ([("One pass after the rain per orbit, ", {"bold": True}), ("from a later NASA processing release.", {})],
         "We report the rise only where both orbits see it on their own, and the release change is in our limits."),
        ([("No fire forecast, no canal advice.", {"bold": True})],
         "Inside drained land an early fall did not separate later fire from no fire, so we withdrew the claim."),
        ([("Fire returns, but we cannot say why.", {"bold": True})],
         f"{num.share('fire_repeat_share_on_peat_west')} of this year's fire on western peat fell on the "
         f"{num.share('fire_earlier_share_on_peat_west')} that burned in 2015, 2019 or 2023. Fire off peat is mapped too."),
    ])
    framed(s, fig / "fig_water_table.png", Inches(8.3), Inches(1.65), Inches(4.43), "Water table figure")
    text(s, Inches(8.3), Inches(4.25), Inches(4.43), Inches(1.0),
         "The bridge: a rainfall-driven water-table model, run on 2026 rain beside the radar. Support, not validation.",
         size=12, color=DIM)
    footer(s, 6, "Hirano groundwater record (CC BY 4.0), GPM IMERG, NISAR L2 GCOV. Full limits: docs/LIMITS.md.", draft)
    s.notes_slide.notes_text_frame.text = "The limits, each with what we did about it."

    # 7. What comes next
    s = prs.slides.add_slide(blank)
    background(s, BG)
    title(s, "What NISAR could do next")
    nxt = [
        [("Ground truth first. ", {"bold": True, "color": INK}), "A sixty-visit field protocol, in the late dry season and after the first rain."],
        [("Years, not months. ", {"bold": True, "color": INK}), "Subsidence by interferometry over whole peat domes, and every dry season set against wet years."],
        [("Anywhere. ", {"bold": True, "color": INK}), "The pipeline takes any bounding box; not yet run on a second site."],
    ]
    text(s, M, Inches(1.8), Inches(5.6), Inches(3.6), nxt, size=17, color=DIM, space_after=16)
    framed(s, fig / "app_room.jpg", Inches(6.55), Inches(1.75), Inches(6.18), "App entry view")   # 1915 x 900 px
    text(s, Inches(6.55), Inches(4.75), Inches(6.18), Inches(0.5),
         "The app's entry view: an illustrative scene made with SI, with the live dashboard on its screens.",
         size=12, color=DIM)
    links = [
        [("Open the map  ", {"bold": True, "color": INK}), (APP_URL, {"bold": True, "link": APP_URL})],
        [("Code and data  ", {"bold": True, "color": INK}), (CODE_URL, {"bold": True, "link": CODE_URL})],
    ]
    text(s, M, Inches(5.45), Inches(12.0), Inches(0.9), links, size=15, color=DIM, space_after=6)
    footer(s, 7, "Made with Super Intelligence (SI) assistance from NASA and ISRO NISAR L2 GCOV data. All code and data open.", draft)
    s.notes_slide.notes_text_frame.text = "Next steps and links."

    link_colour(prs, "5AA9EE")
    prs.save(a.out)
    print(f"wrote {a.out} ({'final' if a.final else 'draft'}); numbers from {len(set(num.used))} validation keys:")
    for k in sorted(set(num.used)):
        print(f"   {k} = {num.v[k]['value']} ({num.v[k].get('status')})")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--figures", default="submission/figures", type=Path)
    p.add_argument("--validation", default="pipeline/out/validation.json", type=Path)
    p.add_argument("--ontology", default="pipeline/fusion/ontology.json", type=Path)
    p.add_argument("--out", default="submission/deck.pptx", type=Path)
    p.add_argument("--final", action="store_true", help="use only keys marked final, and drop the draft tag")
    build(p.parse_args())
