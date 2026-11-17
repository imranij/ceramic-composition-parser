"""Shared print-journal house style for the authored Visio figures.

A paper's build_figures_visio.py keeps its own layout code and its own Sheet
class; this module restyles that Sheet in place.  Three things are done:

  1. PALETTE REMAP (applied textually by the patcher, before `class Sheet` is
     read, so that both `fill=BLUE` default arguments and `s.card(..., ROSE)`
     call sites pick up the new value).  Every pastel card fill collapses to
     white, every mid or dark chroma collapses to dark blue, and neutral greys
     are left alone so chart bars and hairlines keep their tone.

  2. METHOD OVERRIDES installed by `install()`:
       * arrow()  -> a solid dark-blue BLOCK arrow for axis-aligned runs, which
                     is what reads at journal column width.  Diagonal runs, and
                     any dashed run, stay as hairlines with a stick head.
       * band()   -> a lightweight dashed enclosure with no fill, for the boxes
                     that group several items.
       * lane()/lanehead() -> pale blue tab with dark blue lettering, replacing
                     the filled slate gutter.
       * save()   -> wrapped so every exported PDF has its fonts embedded.

  3. TYPE is Times New Roman, matching the body text of the manuscripts.

Colour discipline: white grounds, dark blue flow, one pale blue tint, neutral
grey only for baseline chart series.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

FONT_NAME = "Times New Roman"

WHITE = (255, 255, 255)
INK = (0, 0, 0)
NAVY = (23, 54, 93)         # block arrows, emphasis, stage lettering
NAVY_TX = (18, 44, 78)
PALE = (232, 239, 247)      # the one permitted tint ("whitish blue")
EDGE = (38, 52, 72)         # box outlines
DASH = (143, 161, 184)      # lightweight dashed group enclosures

# Block-arrow proportions, in inches.
BIG = dict(sw=0.17, hw=0.42, head=0.14)
MED = dict(sw=0.11, hw=0.27, head=0.11)
MIN_BLOCK = 0.085           # shorter than this stays a hairline arrow


# ---------------------------------------------------------------- palette ---

import re as _re

# Constants whose value carries a fixed meaning and must survive untouched.
# The house-palette names are included so that a chart hand-tuned to use
# PALE/NAVY for its two series is not flattened again by a later re-patch.
_KEEP = {"WHITE", "INK", "BLACK", "PALE", "NAVY", "NAVY_TX", "EDGE", "DASH"}
# Neutral tones: chart baseline series, hairlines, gridlines, axes.  These stay
# as they are so a grouped bar chart keeps a readable navy-vs-grey contrast.
_NEUTRAL = _re.compile(
    r"(GREY|GRAY|RULE|GRID|AXIS|TICK|_BAR$|^BAR|SHADE|HAIR)")


def classify(c, name=""):
    """Map an author's original RGB onto the restricted house palette.

    Keyed on the constant's NAME rather than on saturation: several papers
    define near-neutral pastels (e.g. a light green at chroma 14) that a purely
    chromatic test would wrongly pass through as grey.
    """
    if name in _KEEP or _NEUTRAL.search(name):
        return tuple(c)
    lum = (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255.0
    return WHITE if lum > 0.82 else NAVY


# ------------------------------------------------------------ file moves ---

def _retry(fn, *a, tries=12, delay=0.25, **kw):
    """OneDrive opens files moments after Visio writes them, so renames and
    deletes fail intermittently with WinError 32.  Retrying briefly is enough."""
    for i in range(tries):
        try:
            return fn(*a, **kw)
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(delay)


def _promote(tmp, final):
    try:
        _retry(tmp.replace, final)
        return
    except PermissionError:
        pass
    _retry(shutil.copyfile, tmp, final)
    try:
        _retry(tmp.unlink, missing_ok=True)
    except PermissionError:
        pass


# --------------------------------------------------------- font embedding ---

GS_CANDIDATES = (
    r"C:\Program Files\MiKTeX\miktex\bin\x64\mgs.exe",
    r"C:\Program Files\gs\gs10.03.1\bin\gswin64c.exe",
    "gswin64c",
    "gs",
)


def _ghostscript():
    for c in GS_CANDIDATES:
        p = c if (os.path.isabs(c) and os.path.exists(c)) else shutil.which(c)
        if p:
            return p
    return None


def embed_fonts(pdf):
    """Re-write `pdf` in place with every font embedded and subset.

    Visio embeds a face only when a run needs a glyph outside WinAnsi, so plain
    ASCII text comes out referencing Times New Roman without embedding it, which
    publishers reject.  Ghostscript is pointed at C:/Windows/Fonts so it embeds
    the genuine face instead of substituting its own Times clone.  Page geometry
    is preserved exactly.
    """
    pdf = Path(pdf)
    gs = _ghostscript()
    if gs is None:
        return False
    tmp = pdf.with_name(pdf.stem + "_emb.pdf")
    cmd = [gs, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite",
           "-dPDFSETTINGS=/prepress", "-dEmbedAllFonts=true", "-dSubsetFonts=true",
           "-dAutoRotatePages=/None", "-dCompatibilityLevel=1.5",
           "-sFONTPATH=C:/Windows/Fonts",
           # Ghostscript reads these as PostScript strings, so they need forward
           # slashes even though the tree lives under a Windows path.
           f"-sOutputFile={tmp.as_posix()}", pdf.as_posix()]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not tmp.exists():
        print(f"  warning: font embedding failed for {pdf.name}: "
              f"{(r.stderr or r.stdout).strip()[:160]}")
        try:
            _retry(tmp.unlink, missing_ok=True)
        except PermissionError:
            pass
        return False
    _promote(tmp, pdf)
    return True


# ------------------------------------------------------- in-figure titles ---

def _load_strip_stems():
    """Figure stems whose in-figure title repeats the LaTeX caption.

    Journals want the title in the caption, not burnt into the artwork, and a
    line that says exactly what the caption says is pure duplication.  The list
    is explicit rather than inferred, so a rebuild cannot start deleting
    lettering that turns out to carry something the caption does not.
    """
    import json
    p = Path(__file__).resolve().parent / "strip_titles.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return set()
    out = set()
    for d in data:
        out.add(d["stem"] if isinstance(d, dict) else str(d))
    return out


STRIP_TITLE_STEMS = _load_strip_stems()
TITLE_TOP_MARGIN = 0.07     # white left above the content once the title goes


def _geo(sh):
    """(x0, y0, x1, y1) of a shape, or None."""
    try:
        px = sh.CellsU("PinX").ResultIU
        py = sh.CellsU("PinY").ResultIU
        w = sh.CellsU("Width").ResultIU
        h = sh.CellsU("Height").ResultIU
        lx = sh.CellsU("LocPinX").ResultIU
        ly = sh.CellsU("LocPinY").ResultIU
    except Exception:
        return None
    x0, y0 = px - lx, py - ly
    return x0, y0, x0 + w, y0 + h


def drop_title(sheet):
    """Delete the in-figure title and pull the page top down to the content.

    Applies the same tests as the offline audit: the largest plain-text line
    across the top, spanning a good part of the width, outside every box and not
    an equation.  Returns True when something was removed.
    """
    page, pw, ph = sheet.page, sheet.width, sheet.height
    n = page.Shapes.Count
    shapes = [page.Shapes.Item(i) for i in range(1, n + 1)]
    info = []
    for sh in shapes:
        g = _geo(sh)
        if g is None:
            continue
        try:
            txt = (sh.Text or "").strip()
        except Exception:
            txt = ""
        try:
            fp = sh.CellsU("FillPattern").ResultIU
            lp = sh.CellsU("LinePattern").ResultIU
        except Exception:
            fp = lp = 1
        try:
            pt = sh.CellsU("Char.Size").Result("pt") if txt else 0.0
        except Exception:
            pt = 0.0
        info.append({"sh": sh, "g": g, "txt": txt, "pt": pt,
                     "plain": fp == 0 and lp == 0})
    texts = [d for d in info if d["txt"]]
    if not texts:
        return False
    biggest = max(d["pt"] for d in texts)
    page_area = pw * ph
    inner = [d["g"] for d in info
             if not (d["plain"] and d["txt"])
             and (d["g"][2] - d["g"][0]) * (d["g"][3] - d["g"][1]) < page_area * 0.70]

    def in_box(g):
        cx, cy = (g[0] + g[2]) / 2, (g[1] + g[3]) / 2
        return any(b[0] - 0.02 <= cx <= b[2] + 0.02
                   and b[1] - 0.02 <= cy <= b[3] + 0.02 for b in inner)

    def prose(t):
        if "=" in t:
            return False
        letters = sum(c.isalpha() or c.isspace() for c in t)
        return letters / max(len(t), 1) >= 0.75

    cands = [d for d in texts
             if d["plain"] and d["pt"] >= biggest - 0.2
             and d["g"][3] >= ph * 0.82
             and (d["g"][2] - d["g"][0]) >= pw * 0.35
             and len(d["txt"]) >= 15
             and not in_box(d["g"]) and prose(d["txt"])]
    if not cands:
        return False
    victim = max(cands, key=lambda d: (d["g"][3], d["g"][2] - d["g"][0]))
    try:
        victim["sh"].Delete()
    except Exception:
        return False

    # pull the page top down onto what is left; nothing moves, the sheet shrinks
    tops = [d["g"][3] for d in info if d is not victim
            and (d["g"][2] - d["g"][0]) * (d["g"][3] - d["g"][1]) < page_area * 0.70]
    if tops:
        new_h = max(tops) + TITLE_TOP_MARGIN
        if 0.5 < new_h < ph:
            sheet.height = new_h
    return True


# ------------------------------------------------------------- overrides ---

def install(Sheet, g=None):
    """Restyle `Sheet` in place.  `g` is the generator module's globals()."""

    def _rgb(c):
        return f"RGB({c[0]},{c[1]},{c[2]})"

    def _poly(self, pts, fill):
        sh = self.page.DrawPolyline(pts, 0)
        sh.CellsU("FillPattern").FormulaU = "1"
        sh.CellsU("FillForegnd").FormulaU = _rgb(fill)
        sh.CellsU("LinePattern").FormulaU = "0"
        return sh

    def barrow(self, x1, y1, x2, y2, sw=0.12, hw=0.30, head=0.13, color=NAVY):
        """Axis-aligned block arrow from (x1,y1) to (x2,y2)."""
        if abs(x2 - x1) < abs(y2 - y1):                     # vertical
            s = -1 if y2 < y1 else 1
            nk = y2 - s * head
            pts = [x1 - sw / 2, y1, x1 + sw / 2, y1,
                   x1 + sw / 2, nk, x1 + hw / 2, nk,
                   x1, y2,
                   x1 - hw / 2, nk, x1 - sw / 2, nk, x1 - sw / 2, y1]
        else:                                               # horizontal
            s = -1 if x2 < x1 else 1
            nk = x2 - s * head
            pts = [x1, y1 - sw / 2, nk, y1 - sw / 2,
                   nk, y1 - hw / 2, x2, y1, nk, y1 + hw / 2,
                   nk, y1 + sw / 2, x1, y1 + sw / 2, x1, y1 - sw / 2]
        return _poly(self, pts, color)

    Sheet._poly = _poly
    Sheet.barrow = barrow

    # ---- band(): lightweight dashed enclosure, no fill -------------------
    if hasattr(Sheet, "band"):
        def band(self, x, y, w, h, *a, **kw):
            sh = self.page.DrawRectangle(x, y, x + w, y + h)
            sh.CellsU("FillPattern").FormulaU = "0"
            sh.CellsU("LineColor").FormulaU = _rgb(DASH)
            sh.CellsU("LineWeight").FormulaU = "0.5 pt"
            sh.CellsU("LinePattern").FormulaU = "2"
            try:
                sh.SendToBack()
            except Exception:
                pass
            return sh
        Sheet.band = band

    # ---- lane()/lanehead(): pale tab, dark blue lettering ----------------
    # The helper that applies character formatting is spelled differently across
    # the papers (_fmt in the inline Sheet classes, _set_text_format in the
    # shared visio_common), so resolve it rather than assuming a name.
    _FMT_NAMES = ("_fmt", "_set_text_format", "_format_text", "_apply_text")

    def _fmt_of(self):
        for n in _FMT_NAMES:
            f = getattr(self, n, None)
            if callable(f):
                return f
        return None

    for nm in ("lane", "lanehead"):
        if not hasattr(Sheet, nm):
            continue

        def _lane(self, x, y, w, h, caption="", size=6.2, *a, **kw):
            sh = self.page.DrawRectangle(x, y, x + w, y + h)
            sh.CellsU("FillForegnd").FormulaU = _rgb(PALE)
            sh.CellsU("LineColor").FormulaU = _rgb(EDGE)
            sh.CellsU("LineWeight").FormulaU = "0.5 pt"
            if caption:
                sh.Text = caption
                fmt = _fmt_of(self)
                if fmt is not None:
                    try:
                        fmt(sh, size, True, NAVY_TX, "center", "middle", 0.03)
                    except TypeError:
                        # a few variants take no margin argument
                        fmt(sh, size, True, NAVY_TX, "center", "middle")
            return sh
        setattr(Sheet, nm, _lane)

    # ---- save(): embed fonts in the exported PDF ------------------------
    _orig_save = Sheet.save

    def _outdir(stem):
        """Locate the directory a generator just wrote `stem` into.

        The papers do not agree on a name for it -- FIGURES, FIGURES_DIR and
        MANUSCRIPT all appear -- so any module-level Path that actually holds
        the new PDF is accepted.
        """
        for key in ("FIGURES", "FIGURES_DIR", "MANUSCRIPT", "FIG_DIR", "OUTDIR"):
            d = (g or {}).get(key)
            if isinstance(d, Path) and (d / f"{stem}.pdf").exists():
                return d
        for v in (g or {}).values():
            if isinstance(v, Path) and v.is_dir() and (v / f"{stem}.pdf").exists():
                return v
        return None

    def save(self, stem, *a, **kw):
        # done before the generator's own save, so the page it writes is already
        # the shorter one
        if stem in STRIP_TITLE_STEMS:
            try:
                drop_title(self)
            except Exception as e:
                print(f"  note: could not drop the title of {stem}: {e!r}"[:140])
        out = _orig_save(self, stem, *a, **kw)
        figdir = _outdir(stem)
        if figdir is not None:
            figdir = Path(figdir)
            pdf = figdir / f"{stem}.pdf"
            if pdf.exists() and embed_fonts(pdf):
                print(f"  embedded fonts in {pdf.name}")
            # OneDrive re-creates the scratch files the original save() renamed
            # away, so sweep them rather than leaving them beside the figures
            for junk in figdir.glob(f"{stem}_tmp.*"):
                try:
                    _retry(junk.unlink, missing_ok=True)
                except PermissionError:
                    pass
        return out

    Sheet.save = save

    # ---- arrow(): block arrow for solid axis-aligned runs -----------------
    # A few papers draw their connectors purely with line() and never define
    # arrow(); those need per-figure attention rather than an override.
    if not hasattr(Sheet, "arrow"):
        return Sheet

    _orig_arrow = Sheet.arrow

    def arrow(self, x1, y1, x2, y2, dashed=False, weight=0.7, color=None,
              *a, **kw):
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        span = max(dx, dy)
        axis_aligned = min(dx, dy) < 0.012
        if dashed or not axis_aligned or span < MIN_BLOCK:
            # dashed runs carry a distinct meaning, and a stubby block arrow
            # reads as a blob, so both stay hairlines
            return _orig_arrow(self, x1, y1, x2, y2, dashed, weight,
                               NAVY if color is None else color, *a, **kw)
        # Block arrows are dark blue, except that a caller asking explicitly for
        # black gets black: a figure whose legend distinguishes several kinds of
        # edge needs more than one ink, and black is the only other one allowed.
        ink = NAVY
        if color is not None:
            lum = (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]) / 255.0
            if lum < 0.18:
                ink = INK
        p = BIG if span >= 0.55 else MED
        # Keep the head narrower than the run is long, or a short arrow comes
        # out wider than it is tall and reads as a squat blob.
        hw = min(p["hw"], span * 0.85)
        return barrow(self, x1, y1, x2, y2, sw=min(p["sw"], hw * 0.42),
                      hw=hw, head=min(p["head"], span * 0.62), color=ink)

    Sheet.arrow = arrow

    # ---- path(): routed connectors stay hairline end to end --------------
    # A multi-segment run whose leading segments are hairlines but whose final
    # segment is a block arrow reads as a thin line sprouting a fat head, so
    # routed paths keep a stick head throughout.  Block arrows are reserved for
    # the direct stage-to-stage runs drawn by arrow().
    if hasattr(Sheet, "path"):
        def path(self, pts, dashed=False, weight=0.7, color=None, *a, **kw):
            col = NAVY if color is None else color
            for i in range(len(pts) - 1):
                (x1, y1), (x2, y2) = pts[i], pts[i + 1]
                if i == len(pts) - 2:
                    _orig_arrow(self, x1, y1, x2, y2, dashed, weight, col)
                else:
                    self.line(x1, y1, x2, y2, dashed, weight, col)
        Sheet.path = path

    return Sheet
