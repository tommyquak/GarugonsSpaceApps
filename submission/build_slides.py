# Written with Super Intelligence (SI) assistance.
"""Build the seven-slide demo deck (track 6) as a .pptx, ready to upload to Google Slides.

Every number on a slide is read from validation.json; none is typed here. The order is the
one agreed on issue #36: the problem, what NISAR sees, the season, the app, why believe it,
what we do not see, what comes next. Claims stay inside docs/AUDIT.md "What we can still claim".

    python submission/build_slides.py --figures submission/figures --validation pipeline/out/validation.json \\
        --out submission/deck.pptx            # draft: exploratory numbers, tagged on every slide
    python submission/build_slides.py ... --final   # only keys marked final; stops if one is missing

Figures and app GIFs come from Tommy's release: gh release download figures-v3 --dir submission/figures
slide 7 also needs app_room.jpg, a screenshot of the app's entry view (Kalent), in the same folder.
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

INK = RGBColor(0x16, 0x19, 0x1D)
PAPER = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x5B, 0x63, 0x6B)
MUTED_ON_INK = RGBColor(0xA9, 0xB0, 0xB8)
SOFT_ON_INK = RGBColor(0xE6, 0xE8, 0xEB)
RULE = RGBColor(0xD9, 0xDC, 0xE0)
CANOPY = RGBColor(0xC9, 0xD3, 0xC4)
TRUNK = RGBColor(0x8C, 0x93, 0x99)
FALL = RGBColor(0x8A, 0x5A, 0x2B)   # the fall in HH: sand to brown, as in the app
SAND = RGBColor(0xE8, 0xC9, 0x8E)
FIRE = RGBColor(0xD9, 0x3A, 0x2B)   # fire detections only
RAIN = RGBColor(0x3D, 0x8F, 0xD6)   # rain
DRAFT = RGBColor(0xB2, 0x6A, 0x00)

FONT = "Archivo"
W, H = Inches(13.333), Inches(7.5)
M = Inches(0.6)
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


def text(slide, x, y, w, h, runs, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space_after=0, name=None):
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
            f.name = FONT
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


def title(slide, words, color=INK):
    text(slide, M, Inches(0.45), W - 2 * M, Inches(1.0), words, size=30, bold=True, color=color,
         anchor=MSO_ANCHOR.TOP, name="Title")


def footer(slide, n, source, draft, dark=False):
    c = MUTED_ON_INK if dark else MUTED
    text(slide, M, H - Inches(0.5), Inches(10.5), Inches(0.3), source, size=10, color=c, name="Source")
    text(slide, W - M - Inches(1.0), H - Inches(0.5), Inches(1.0), Inches(0.3), f"{n} / 7", size=10, color=c,
         align=PP_ALIGN.RIGHT, name="Page")
    if draft:
        text(slide, W - M - Inches(3.0), Inches(0.12), Inches(3.0), Inches(0.25), "Draft: exploratory numbers",
             size=10, bold=True, color=DRAFT, align=PP_ALIGN.RIGHT, name="Draft tag")


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


def radar_diagram(slide, x, y):
    """How the two echoes come back: HH bounces between ground and trunk, HV comes mostly from the woody canopy."""
    ground_y = y + Inches(3.9)
    shape(slide, MSO_SHAPE.RECTANGLE, x, ground_y, Inches(5.6), Inches(0.5), SAND)
    text(slide, x + Inches(0.15), ground_y + Inches(0.1), Inches(3.5), Inches(0.3), "peat surface, drying", size=12, color=FALL)
    for i, tx in enumerate((0.9, 2.5, 4.1)):
        cx = x + Inches(tx)
        shape(slide, MSO_SHAPE.RECTANGLE, cx, y + Inches(1.9), Inches(0.14), Inches(2.0), TRUNK)
        shape(slide, MSO_SHAPE.OVAL, cx - Inches(0.62), y + Inches(1.1), Inches(1.38), Inches(1.0), CANOPY)
    shape(slide, MSO_SHAPE.RECTANGLE, x + Inches(4.4), y + Inches(0.1), Inches(0.38), Inches(0.12), TRUNK)
    shape(slide, MSO_SHAPE.RECTANGLE, x + Inches(5.42), y + Inches(0.1), Inches(0.38), Inches(0.12), TRUNK)
    shape(slide, MSO_SHAPE.RECTANGLE, x + Inches(4.8), y, Inches(0.6), Inches(0.32), INK)
    text(slide, x + Inches(2.0), y + Inches(0.02), Inches(2.3), Inches(0.3), "NISAR, L-band", size=12, color=MUTED,
         align=PP_ALIGN.RIGHT)
    # HH: down to the ground, across to the trunk, back up
    line(slide, x + Inches(4.9), y + Inches(0.32), x + Inches(3.3), ground_y, FALL, 2.5, arrow=True)
    line(slide, x + Inches(3.3), ground_y, x + Inches(2.64), y + Inches(3.2), FALL, 2.5, arrow=True)
    line(slide, x + Inches(2.64), y + Inches(3.2), x + Inches(4.95), y + Inches(0.32), FALL, 2.5, arrow=True)
    text(slide, x + Inches(1.15), y + Inches(2.55), Inches(1.25), Inches(0.9),
         [[("HH", {"bold": True, "color": FALL})], "ground", "and trunk"], size=12, color=FALL)
    # HV: down into the canopy and back
    line(slide, x + Inches(5.3), y + Inches(0.32), x + Inches(4.6), y + Inches(1.35), INK, 2.0, arrow=True)
    text(slide, x + Inches(5.25), y + Inches(0.75), Inches(1.0), Inches(0.6),
         [[("HV", {"bold": True})], "woody", "canopy"], size=12, color=INK)


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
    background(s, INK)
    picture(s, fig / "fig_map.png", Inches(6.55), Inches(1.6), w=Inches(6.2), name="One-look map")   # 1617 x 1032 px
    text(s, M, Inches(0.9), Inches(5.6), Inches(1.0), "Dry Season Waltz", size=44, bold=True, color=PAPER)
    text(s, M, Inches(1.95), Inches(5.6), Inches(2.2),
         "NISAR lets anyone watch a peat dry season through cloud and smoke: an open map of where the radar "
         "echo fell, where fire was detected and what changed with the rain, with its evidence and its limits attached.",
         size=17, color=SOFT_ON_INK)
    text(s, M, Inches(4.0), Inches(5.6), Inches(1.6),
         ["Every dry season, drained peat in Borneo is at its most flammable, some of it burns, and the haze reaches "
          "cities across the region. Cloud, then smoke, hides the ground from optical satellites just then."],
         size=14, color=MUTED_ON_INK)
    text(s, M, Inches(6.35), Inches(5.6), Inches(0.3), "Team Garugons · NASA Space Apps 2026 · Dancing with the SARs",
         size=12, color=MUTED_ON_INK)
    footer(s, 1, "", draft, dark=True)
    s.notes_slide.notes_text_frame.text = (
        "The problem and the one takeaway. Map: where HH fell by 1 dB or more, mid July to mid October 2026, "
        "Central Kalimantan, with the PEATMAP outline.")

    # 2. What NISAR sees: the problem in one picture, and how the radar gets through
    s = prs.slides.add_slide(blank)
    background(s, PAPER)
    title(s, "Cloud and smoke hide the ground from optical satellites. NISAR's radar sees through them")
    picture(s, fig / "fig_cloud.png", M, Inches(1.6), w=Inches(5.95), name="Cloud against radar figure")
    picture(s, fig / "explainer.gif", Inches(6.78), Inches(1.6), w=Inches(5.95), name="Radar explainer animation")
    text(s, M, Inches(5.1), Inches(5.95), Inches(1.5),
         [[("Every 12 days, day or night. ", {"bold": True}),
           "The same ground on the same day: smoke and cloud for the optical satellite, the land for the radar."]],
         size=14, color=INK)
    text(s, Inches(6.78), Inches(5.1), Inches(5.95), Inches(1.5),
         [[("HH ", {"bold": True, "color": FALL}),
           "carries a bounce between the ground and the trunks that weakens as the surface dries (Hess et al. 1990; "
           "Kim et al. 2017). "], [("HV ", {"bold": True}),
           "comes mostly from woody vegetation, but responds to moisture too. A schematic, not data."]],
         size=14, color=INK, space_after=4)
    footer(s, 2, "VIIRS Corrected Reflectance (NASA GIBS), NISAR L2 GCOV (ASF DAAC). Animation made with SI assistance.", draft)
    s.notes_slide.notes_text_frame.text = "The problem in one picture, and how the radar sees the ground. Physics claims are the audited ones only."

    # 3. The season in one picture
    s = prs.slides.add_slide(blank)
    background(s, PAPER)
    title(s, "Through the dry season HH fell steadily on peat, then rose within days of the first heavy rain")
    picture(s, fig / "fig_season.png", M, Inches(1.65), w=Inches(8.9), name="Season figure")
    dawn, dusk = num.db("recovery_hh_median_rebound_west_125"), num.db("recovery_hh_median_rebound_west_061")
    rise, rise_where = (dawn, "on both orbits") if dawn == dusk else (f"{dawn} and {dusk}", "dawn and dusk orbits")
    side = [
        [(num.km2("fell_1db_km2_on_peat_west"), {"bold": True, "size": 22, "color": FALL})],
        ["of mapped peat in the west box fell by 1 dB or more on both orbits"],
        [(num.km2("fell_1db_km2_on_peat_east"), {"bold": True, "size": 22, "color": FALL})],
        ["in the east box"],
        [(rise, {"bold": True, "size": 22, "color": RAIN})],
        [f"rise in HH on the first pass after the rain, {rise_where}, and not on the pass before"],
    ]
    text(s, Inches(9.85), Inches(1.9), Inches(2.9), Inches(4.8), side, size=14, color=INK, space_after=6)
    footer(s, 3, "Figure: pipeline/figures.py. NISAR L2 GCOV (ASF DAAC), GPM IMERG (GES DISC), PEATMAP (CC BY 4.0).", draft)
    s.notes_slide.notes_text_frame.text = "The season at a glance: the fall, deep forest flat as the yardstick, daily rain underneath."

    # 4. The app
    s = prs.slides.add_slide(blank)
    background(s, PAPER)
    title(s, "An open map anyone can play through the season, then check place by place")
    picture(s, fig / "demo_season.gif", M, Inches(1.65), w=Inches(8.0), name="Season demo")
    picture(s, fig / "demo_check.gif", Inches(9.0), Inches(4.05), w=Inches(3.73), name="Where to check demo")
    items = [
        [("Play the season. ", {"bold": True}), "Every pass on both orbits; fire builds up beside the fall."],
        [("Where to check. ", {"bold": True}),
         "1 km blocks labelled by what was seen, ranked, with the evidence behind each, as CSV or GeoJSON."],
        [("Open the map", {"bold": True, "link": APP_URL})],
    ]
    text(s, Inches(9.0), Inches(1.7), Inches(3.73), Inches(2.3), items, size=14, color=INK, space_after=8)
    footer(s, 4, "Live app: tommyquak.github.io/GarugonsSpaceApps. Basemap: Sentinel-2 cloudless 2016 by EOX, CC BY 4.0.", draft)
    s.notes_slide.notes_text_frame.text = "GIFs recorded from the live app (figures-v3): the season with fire building up, and Where to check."

    # 5. Why believe it
    s = prs.slides.add_slide(blank)
    background(s, PAPER)
    title(s, "Why believe it: two orbits agree, and an audit we asked for made the answer smaller")
    picture(s, fig / "fig_orbits.png", M, Inches(1.7), w=Inches(5.95), name="Orbits figure")
    picture(s, fig / "fig_start.png", Inches(6.78), Inches(1.7), w=Inches(5.95), name="Start figure")
    text(s, M, Inches(5.2), Inches(5.95), Inches(1.4),
         f"Dawn and dusk orbits look from opposite sides, hours apart, and agree block by block on where HH fell: "
         f"Spearman r = {num.get('track5_west_orbit_spearman'):.2f} in the west box, {num.get('track5_east_orbit_spearman'):.2f} "
         f"in the east (the scatter shows Pearson r).",
         size=14, color=INK)
    text(s, Inches(6.78), Inches(5.2), Inches(5.95), Inches(1.4),
         "Half way through, an independent audit found our first start date came just after rain. We now start "
         "from the first rain-free passes, and published the audit with our response.",
         size=14, color=INK)
    footer(s, 5, "Figures: pipeline/figures.py. Audit and response: docs/AUDIT.md.", draft)
    s.notes_slide.notes_text_frame.text = "Validity: independent orbits, and the audit as evidence, not as the headline."

    # 6. What we do not see
    s = prs.slides.add_slide(blank)
    background(s, PAPER)
    title(s, "What the radar cannot tell us yet")
    limits = [
        [("Not checked on the ground. ", {"bold": True}),
         "A fall in HH is not a measured water table. About sixty dipwell visits would calibrate the map or prove it wrong."],
        [("One pass after the rain per orbit, ", {"bold": True}),
         "from a later NASA processing release than the dry passes."],
        [("No fire forecast, no canal advice. ", {"bold": True}),
         "An early fall did not separate later fire from no fire inside drained land."],
        [("Fire returns, but we cannot say why. ", {"bold": True}),
         f"On western peat, {num.share('fire_repeat_share_on_peat_west')} of this year's fire fell on the "
         f"{num.share('fire_earlier_share_on_peat_west')} that burned in 2015, 2019 or 2023. Fire off peat is mapped too."],
    ]
    text(s, M, Inches(1.75), Inches(5.4), Inches(4.8), limits, size=15, color=INK, space_after=14)
    picture(s, fig / "fig_water_table.png", Inches(6.35), Inches(1.75), w=Inches(6.4), name="Water table figure")
    text(s, Inches(6.35), Inches(5.45), Inches(6.4), Inches(0.9),
         "The closest we can get without fieldwork: a rainfall-driven water-table model from a published gauge "
         "record. Support, not validation.", size=13, color=MUTED)
    footer(s, 6, "Hirano groundwater record (CC BY 4.0), GPM IMERG, NISAR L2 GCOV. Limits: docs/LIMITS.md.", draft)
    s.notes_slide.notes_text_frame.text = "The limits, and the ground truth still missing."

    # 7. What comes next
    s = prs.slides.add_slide(blank)
    background(s, INK)
    title(s, "What NISAR could do next", color=PAPER)
    nxt = [
        [("Ground truth first. ", {"bold": True, "color": PAPER}), "A sixty-visit field protocol, in the late dry season and after the first rain."],
        [("Years, not months. ", {"bold": True, "color": PAPER}), "Subsidence by interferometry over whole peat domes, and every dry season set against wet years."],
        [("Anywhere. ", {"bold": True, "color": PAPER}), "The pipeline takes any bounding box: another peatland is one command away."],
    ]
    text(s, M, Inches(1.8), Inches(5.6), Inches(3.6), nxt, size=17, color=SOFT_ON_INK, space_after=16)
    picture(s, fig / "app_room.jpg", Inches(6.55), Inches(1.75), w=Inches(6.18), name="App entry view")   # 1915 x 900 px
    text(s, Inches(6.55), Inches(4.75), Inches(6.18), Inches(0.5),
         "The app's entry view: an illustrative scene made with SI, with the live dashboard on its screens.",
         size=12, color=MUTED_ON_INK)
    links = [
        [("Open the map  ", {"bold": True, "color": PAPER}), (APP_URL, {"bold": True, "link": APP_URL})],
        [("Code and data  ", {"bold": True, "color": PAPER}), (CODE_URL, {"bold": True, "link": CODE_URL})],
    ]
    text(s, M, Inches(5.45), Inches(12.0), Inches(0.9), links, size=15, color=SOFT_ON_INK, space_after=6)
    footer(s, 7, "Made with Super Intelligence (SI) assistance from NASA and ISRO NISAR L2 GCOV data. All code and data open.", draft, dark=True)
    s.notes_slide.notes_text_frame.text = "Next steps and links."

    link_colour(prs, "2B78BD")
    prs.save(a.out)
    print(f"wrote {a.out} ({'final' if a.final else 'draft'}); numbers from {len(set(num.used))} validation keys:")
    for k in sorted(set(num.used)):
        print(f"   {k} = {num.v[k]['value']} ({num.v[k].get('status')})")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--figures", default="submission/figures", type=Path)
    p.add_argument("--validation", default="pipeline/out/validation.json", type=Path)
    p.add_argument("--out", default="submission/deck.pptx", type=Path)
    p.add_argument("--final", action="store_true", help="use only keys marked final, and drop the draft tag")
    build(p.parse_args())
