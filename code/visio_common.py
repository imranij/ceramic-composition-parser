"""Shared Visio COM helpers for the DDAFGR-IDS manuscript's design figures.

Every figure is drawn at its *final printed size* so that a point of text in the
drawing is a point of text on the page.  This manuscript uses elsarticle with
[margin=1in] geometry, which gives \\linewidth = 469.755pt = 6.50in, so a figure
placed at width=\\linewidth is drawn 6.50in wide and \\includegraphics scales it
by 1.0.  Drawing oversized and letting LaTeX shrink the result is what makes
block-diagram labels unreadable.

Conventions follow the companion project's figures: a dark slate lane gutter on
the left of each band, light banded rows, cards with a bold title over a smaller
detail line, and orthogonal connectors only -- no swooping curves.

Type sizes: 7pt bold lane titles and card titles, 6pt card detail, 5.8pt edge
labels.  Nothing below 5.5pt.
"""

from __future__ import annotations

import sys

from pathlib import Path

import win32com.client


ROOT = Path(__file__).resolve().parents[1]
# The .tex files use \includegraphics{name.pdf} with no path, so the PDFs must
# land next to manuscript.tex.
FIGURES = ROOT / "manuscript"

# Page geometry derived from the document class in manuscript.tex.
LINE_WIDTH_IN = 6.50

# Muted palette; fills stay light enough that 6pt text reads, and the figures
# degrade gracefully in grayscale.
BLUE = (255, 255, 255)
GREEN = (255, 255, 255)
GREEN_DARK = (255, 255, 255)
AMBER = (255, 255, 255)
VIOLET = (255, 255, 255)
ROSE = (255, 255, 255)
BAND = (255, 255, 255)
SLATE = (23, 54, 93)
WHITE = (255, 255, 255)
INK = (26, 26, 26)
RULE = (110, 118, 128)
BAND_RULE = (196, 200, 205)
ACCENT = (23, 54, 93)  # bypass / non-standard edges
COUPLE = (23, 54, 93)  # alpha-beta coupling edges

FONT_NAME = "Times New Roman"


def rgb(color: tuple[int, int, int]) -> str:
    return f"RGB({color[0]},{color[1]},{color[2]})"


class Sheet:
    """A single Visio drawing page sized in inches, origin at bottom-left."""

    def __init__(self, app, name: str, width: float, height: float):
        self.app = app
        self.doc = app.Documents.Add("")
        self.page = self.doc.Pages.Item(1)
        self.page.Name = name
        self.width = width
        self.height = height
        try:
            self.page.AutoSize = False
        except Exception:
            pass
        self._apply_page_size()
        self._font_id = self._resolve_font(FONT_NAME)

    def _apply_page_size(self) -> None:
        sheet = self.page.PageSheet
        sheet.CellsU("DrawingSizeType").FormulaU = "3"  # custom page size
        sheet.CellsU("PageWidth").FormulaU = f"{self.width} in"
        sheet.CellsU("PageHeight").FormulaU = f"{self.height} in"

    def _resolve_font(self, name: str):
        try:
            return self.doc.Fonts.Item(name).ID
        except Exception:
            return None

    def _set_text_format(self, shape, size, bold, color, align, valign, margin) -> None:
        shape.CellsU("Char.Size").FormulaU = f"{size} pt"
        shape.CellsU("Char.Color").FormulaU = rgb(color)
        shape.CellsU("Char.Style").FormulaU = "17" if bold else "0"
        if self._font_id is not None:
            shape.CellsU("Char.Font").FormulaU = str(self._font_id)
        shape.CellsU("Para.HorzAlign").FormulaU = {"left": "0", "center": "1", "right": "2"}[align]
        shape.CellsU("VerticalAlign").FormulaU = {"top": "0", "middle": "1", "bottom": "2"}[valign]
        for cell in ("LeftMargin", "RightMargin", "TopMargin", "BottomMargin"):
            shape.CellsU(cell).FormulaU = f"{margin} in"

    # ---------------------------------------------------------------- shapes

    def rect(self, x, y, w, h, fill=WHITE, line=RULE, weight=0.6, dashed=False, filled=True):
        shape = self.page.DrawRectangle(x, y, x + w, y + h)
        if filled:
            shape.CellsU("FillForegnd").FormulaU = rgb(fill)
        else:
            shape.CellsU("FillPattern").FormulaU = "0"
        shape.CellsU("LineColor").FormulaU = rgb(line)
        shape.CellsU("LineWeight").FormulaU = f"{weight} pt"
        if dashed:
            shape.CellsU("LinePattern").FormulaU = "2"
        return shape

    def text(self, x, y, w, h, content, size=6.0, bold=False, color=INK,
             align="left", valign="middle"):
        shape = self.page.DrawRectangle(x, y, x + w, y + h)
        shape.CellsU("LinePattern").FormulaU = "0"
        shape.CellsU("FillPattern").FormulaU = "0"
        shape.Text = content
        self._set_text_format(shape, size, bold, color, align, valign, 0.0)
        return shape

    def band(self, x, y, w, h, fill=BAND):
        shape = self.rect(x, y, w, h, fill, BAND_RULE, 0.6)
        shape.SendToBack()
        return shape

    def lane(self, x, y, w, h, caption, size=6.5):
        """Dark left-gutter lane title, keeping band labels out of the flow."""
        shape = self.rect(x, y, w, h, SLATE, SLATE, 0.6)
        shape.Text = caption
        self._set_text_format(shape, size, True, WHITE, "center", "middle", 0.03)
        return shape

    def card(self, x, y, w, h, title, detail="", fill=WHITE, title_size=7.0,
             detail_size=6.0, align="left", title_lines=1, line=RULE, weight=0.6):
        """Filled box with a bold title and an optional smaller detail line."""
        shape = self.rect(x, y, w, h, fill, line, weight)
        pad = 0.045
        if detail:
            title_h = title_lines * 0.125
            self.text(x + pad, y + h - pad - title_h, w - 2 * pad, title_h,
                      title, title_size, True, INK, align, "middle")
            self.text(x + pad, y + pad, w - 2 * pad, h - 2 * pad - title_h,
                      detail, detail_size, False, INK, align, "top")
        else:
            self.text(x + pad, y + pad, w - 2 * pad, h - 2 * pad,
                      title, title_size, True, INK, "center", "middle")
        return shape

    def chip(self, x, y, w, h, text, fill=WHITE, size=6.0, bold=False, line=RULE):
        shape = self.rect(x, y, w, h, fill, line)
        shape.Text = text
        self._set_text_format(shape, size, bold, INK, "center", "middle", 0.015)
        return shape

    def bars(self, x, y, w, h, values, fill, baseline_label="", tick_labels=None):
        """Small normalized stem panel used to show GL coefficient profiles.

        `values` are already normalized to [0, 1]; bars are drawn upward from the
        panel floor so the shape of the decay is the readable quantity.
        """
        n = len(values)
        slot = w / n
        bar_w = min(slot * 0.46, 0.055)
        for i, v in enumerate(values):
            cx = x + slot * (i + 0.5)
            bh = max(v * h, 0.006)
            self.rect(cx - bar_w / 2, y, bar_w, bh, fill, fill, 0.3)
        self.line(x, y, x + w, y, weight=0.5)
        if tick_labels:
            for i, lab in enumerate(tick_labels):
                if lab is None:
                    continue
                cx = x + slot * (i + 0.5)
                self.text(cx - 0.09, y - 0.115, 0.18, 0.10, lab, 5.5, False, INK, "center", "middle")
        if baseline_label:
            self.text(x, y - 0.225, w, 0.10, baseline_label, 5.5, False, INK, "center", "middle")

    # ----------------------------------------------------------- connectors

    def line(self, x1, y1, x2, y2, dashed=False, weight=0.7, color=INK):
        shape = self.page.DrawLine(x1, y1, x2, y2)
        shape.CellsU("LineColor").FormulaU = rgb(color)
        shape.CellsU("LineWeight").FormulaU = f"{weight} pt"
        if dashed:
            shape.CellsU("LinePattern").FormulaU = "2"
        return shape

    def arrow(self, x1, y1, x2, y2, dashed=False, weight=0.7, color=INK):
        shape = self.line(x1, y1, x2, y2, dashed, weight, color)
        shape.CellsU("EndArrow").FormulaU = "4"
        shape.CellsU("EndArrowSize").FormulaU = "1"
        return shape

    def path(self, points, dashed=False, weight=0.7, color=INK):
        """Orthogonal polyline; only the final segment carries an arrowhead."""
        shapes = []
        for i in range(len(points) - 1):
            (x1, y1), (x2, y2) = points[i], points[i + 1]
            last = i == len(points) - 2
            fn = self.arrow if last else self.line
            shapes.append(fn(x1, y1, x2, y2, dashed, weight, color))
        return shapes

    def edge_label(self, x, y, w, content, color=INK, size=5.8, align="center"):
        """Edge annotation on an opaque white plate so it never sits on a rule."""
        plate = self.rect(x, y, w, 0.105, WHITE, WHITE, 0.3)
        plate.CellsU("LinePattern").FormulaU = "0"
        self.text(x, y, w, 0.105, content, size, False, color, align, "middle")
        return plate

    # ---------------------------------------------------------------- output

    def _mask_page_border(self) -> None:
        """Hide the 0.75pt black page outline Visio's PDF export always emits.
        No export option suppresses it, so the last shape on the page overdraws
        it in white; keeping the mask in the .vsdx means a manual re-export from
        Visio stays borderless too."""
        shape = self.page.DrawRectangle(0, 0, self.width, self.height)
        shape.CellsU("FillPattern").FormulaU = "0"
        shape.CellsU("LineColor").FormulaU = rgb(WHITE)
        shape.CellsU("LineWeight").FormulaU = "1.6 pt"
        try:
            shape.NameU = "PageBorderMask"
        except Exception:
            pass

    def save(self, stem: str) -> None:
        self._mask_page_border()
        self._apply_page_size()
        vsdx = FIGURES / f"{stem}.vsdx"
        pdf = FIGURES / f"{stem}.pdf"
        tmp_vsdx = FIGURES / f"{stem}_tmp.vsdx"
        tmp_pdf = FIGURES / f"{stem}_tmp.pdf"
        tmp_vsdx.unlink(missing_ok=True)
        tmp_pdf.unlink(missing_ok=True)
        self.doc.SaveAs(str(tmp_vsdx))
        self.doc.ExportAsFixedFormat(1, str(tmp_pdf), 1, 0)
        self.doc.Close()
        tmp_vsdx.replace(vsdx)
        tmp_pdf.replace(pdf)
        print(f"Wrote {vsdx.name} and {pdf.name}  ({self.width:.2f} x {self.height:.2f} in)")


# ---------------------------------------------------------------------------
# Shared print-journal house style: white grounds, dark blue block arrows,
# lightweight dashed group enclosures, Times New Roman, embedded PDF fonts.
# The palette constants above were remapped onto that scheme; these overrides
# supply the block arrows and the dashed enclosures.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))
import visio_house_style as _hs  # noqa: E402

_hs.install(Sheet, globals())


def open_visio():
    app = win32com.client.Dispatch("Visio.Application")
    app.Visible = False
    app.AlertResponse = 7
    app.EventsEnabled = False
    return app


def spread(x0: float, total: float, count: int, gap: float):
    """Evenly divide `total` inches into `count` boxes separated by `gap`."""
    w = (total - gap * (count - 1)) / count
    return [x0 + i * (w + gap) for i in range(count)], w
