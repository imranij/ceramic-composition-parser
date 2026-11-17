"""Build the two schematic figures for Paper 2 in the settled Visio house style.

Figures are drawn at the IEEEtran journal full text width (\\textwidth = 516pt =
7.14in) so each is included with width=\\textwidth and needs no LaTeX scaling.

  1. paper2_pipeline_grounded   -- raw composition string -> grounded record -> outputs
  2. paper2_schema_grounded     -- the CeramicCompositionRecord schema and its grounding relations

Reuses the shared Sheet helper from the fractional-dynamics project. We override
its FIGURES target so exports land in THIS paper's figures/ directory (the .tex
uses \\includegraphics{../figures/...}).
"""

from __future__ import annotations

import sys
from pathlib import Path

# The shared helper used to be imported off a D: drive that is not present on
# every machine; a copy now lives beside this script.
VC_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, VC_DIR)

import visio_common as vc  # noqa: E402

# Draw and export into this paper's figures/ folder, not the helper's home project.
vc.FIGURES = Path(__file__).resolve().parents[1] / "figures"
vc.LINE_WIDTH_IN = 7.14  # IEEEtran journal \textwidth

WIDTH = 7.14
INK = vc.INK
SLATE = vc.SLATE
BLUE = vc.BLUE
GREEN = vc.GREEN
GREEN_DARK = vc.GREEN_DARK
AMBER = vc.AMBER
VIOLET = vc.VIOLET
ROSE = vc.ROSE
BAND = vc.BAND
WHITE = vc.WHITE
RULE = vc.RULE
ACCENT = vc.ACCENT


# --------------------------------------------------------------------------- 1
def build_pipeline(app) -> None:
    """Vertical-band pipeline: input -> parse -> validate -> ground -> output,
    plus a dedicated reject band. Flow reads top-to-bottom; dark left gutters
    name each stage in house style. The reject rail runs down the left margin so
    it never crosses a content card."""
    H = 4.55
    s = vc.Sheet(app, "pipeline", WIDTH, H)

    gx, gw = 0.14, 0.92          # left gutter x, width
    cx = gx + gw + 0.16          # content left (leaves a margin channel for the reject rail)
    cw = WIDTH - cx - 0.14       # content width
    band_h = 0.60
    gap = 0.115
    top = H - 0.16
    railx = cx - 0.09            # reject rail x, in the channel left of the cards

    # Title
    s.text(gx, H - 0.14 - 0.20, WIDTH - 0.28, 0.20,
           "Schema-grounded composition parsing pipeline", 8.5, True, INK, "left", "middle")
    y = top - 0.30

    def band(y0, caption, fill=BAND):
        s.band(cx - 0.02, y0, cw + 0.06, band_h, fill)
        s.lane(gx, y0, gw, band_h, caption)

    # INPUT
    y1 = y - band_h
    band(y1, "INPUT")
    xs, w = vc.spread(cx, cw, 3, 0.14)
    s.card(xs[0], y1 + 0.07, w, band_h - 0.14, "Database formulas",
           "matminer, Castelli, Wolverton (28,100 unique)", BLUE, 6.8, 5.8)
    s.card(xs[1], y1 + 0.07, w, band_h - 0.14, "Literature strings",
           "doped / co-doped / off-stoichiometric notation", BLUE, 6.8, 5.8)
    s.card(xs[2], y1 + 0.07, w, band_h - 0.14, "Thesis ratio expressions",
           "host / additive / alloying mixtures", BLUE, 6.8, 5.8)

    # PARSE
    y2 = y1 - gap - band_h
    band(y2, "PARSE")
    xs, w = vc.spread(cx, cw, 2, 0.16)
    s.card(xs[0], y2 + 0.07, w, band_h - 0.14, "pymatgen Composition",
           "primary backend when available", GREEN, 6.8, 5.8)
    s.card(xs[1], y2 + 0.07, w, band_h - 0.14, "Deterministic fallback grammar",
           "elements, parentheses, decimal stoichiometry", GREEN, 6.8, 5.8)

    # VALIDATE
    y3 = y2 - gap - band_h
    band(y3, "VALIDATE")
    xs, w = vc.spread(cx, cw, 3, 0.14)
    s.card(xs[0], y3 + 0.07, w, band_h - 0.14, "Symbol + separator checks",
           "reject unknown symbols, stray '.' '+'", AMBER, 6.6, 5.7)
    s.card(xs[1], y3 + 0.07, w, band_h - 0.14, "Comma site guard",
           "reject '(Ba,Sr)TiO3': fraction missing", AMBER, 6.6, 5.7)
    s.card(xs[2], y3 + 0.07, w, band_h - 0.14, "Unit interpreter",
           "mol% / wt% / at% (binary mixtures)", AMBER, 6.6, 5.7)

    # GROUND
    y4 = y3 - gap - band_h
    band(y4, "GROUND", VIOLET)
    s.card(cx, y4 + 0.07, cw, band_h - 0.14, "CeramicCompositionRecord",
           "typed roles (host / additive / dopant)  ·  atomic fractions φ  ·  provenance  ·  ambiguity flags",
           VIOLET, 7.0, 5.9)

    # OUTPUT
    y5 = y4 - gap - band_h
    band(y5, "OUTPUT")
    xs, w = vc.spread(cx, cw, 3, 0.14)
    s.card(xs[0], y5 + 0.07, w, band_h - 0.14, "Atomic-fraction vector",
           "CrabNet / Roost feature input", GREEN_DARK, 6.8, 5.8)
    s.card(xs[1], y5 + 0.07, w, band_h - 0.14, "Reduced formula",
           "OPTIMADE-style JSON record", GREEN_DARK, 6.8, 5.8)
    s.card(xs[2], y5 + 0.07, w, band_h - 0.14, "Parser diagnostics",
           "coverage, complexity, audit log", GREEN_DARK, 6.8, 5.8)

    # REJECT (own band, rose)
    y6 = y5 - gap - band_h
    s.band(cx - 0.02, y6, cw + 0.06, band_h, ROSE)
    s.lane(gx, y6, gw, band_h, "REJECT")
    s.card(cx, y6 + 0.07, cw, band_h - 0.14, "Ambiguous / unsupported notation",
           "rejected with a controlled reason and routed to manual review — never silently coerced into a false vector",
           ROSE, 6.9, 5.9)

    # Main flow arrows (down the centre of the content area)
    midx = cx + cw / 2.0
    for ya, yb in [(y1, y2), (y2, y3), (y3, y4), (y4, y5)]:
        s.arrow(midx, ya, midx, yb + band_h, weight=0.9)

    # Reject rail: down the left margin channel from VALIDATE to the REJECT band
    s.path([(cx, y3 + band_h / 2.0), (railx, y3 + band_h / 2.0),
            (railx, y6 + band_h / 2.0), (cx, y6 + band_h / 2.0)],
           dashed=True, weight=0.9, color=ACCENT)

    s.save("paper2_pipeline_grounded")


# --------------------------------------------------------------------------- 2
def build_schema(app) -> None:
    """The CeramicCompositionRecord schema and its grounding relations: an
    accepted and a rejected raw string map onto typed slots that draw their
    values from controlled vocabularies."""
    H = 4.35
    s = vc.Sheet(app, "schema", WIDTH, H)

    s.text(0.14, H - 0.30, WIDTH - 0.28, 0.20,
           "The CeramicCompositionRecord schema and its grounding relations", 8.5, True, INK, "left", "middle")

    # Three columns: examples | record | controlled vocabularies
    col1_x, col1_w = 0.14, 1.72
    col2_x, col2_w = 2.02, 2.86
    col3_x, col3_w = 5.06, WIDTH - 5.06 - 0.14
    top = H - 0.66

    # --- Column headers
    for x, w, cap in [(col1_x, col1_w, "RAW EXPRESSION"),
                      (col2_x, col2_w, "GROUNDED RECORD"),
                      (col3_x, col3_w, "CONTROLLED VOCABULARY")]:
        s.lane(x, top, w, 0.22, cap, 6.4)
    y = top - 0.30

    # --- Column 1: two examples (accepted, rejected)
    ex_h = 0.66
    ax_y = y - ex_h
    s.card(col1_x, ax_y, col1_w, ex_h, "Accepted",
           "0.98 BaTiO3 +\n0.02 Y2O3  (mol%)", GREEN, 6.8, 5.9)
    rj_y = ax_y - 0.9 - ex_h
    s.card(col1_x, rj_y, col1_w, ex_h, "Rejected",
           "(Ba,Sr)TiO3\nsite fraction absent", ROSE, 6.8, 5.9)

    # --- Column 2: the record card with typed field rows
    rec_top = y
    rec_bot = 0.16
    s.rect(col2_x, rec_bot, col2_w, rec_top - rec_bot, VIOLET, RULE, 0.7)
    s.text(col2_x + 0.06, rec_top - 0.22, col2_w - 0.12, 0.18,
           "CeramicCompositionRecord", 7.2, True, INK, "left", "middle")
    fields = [
        ("raw_expression", "original string, verbatim"),
        ("parse_status", "one enum value  →"),
        ("components[]", "{ role, formula, coefficient, unit }"),
        ("  · role", "host / additive / dopant  →"),
        ("  · unit", "mol% / wt% / at% / formula_units"),
        ("atomic_fractions", "{ element: φ },  Σφ = 1"),
        ("provenance", "source, doi, table, row"),
        ("ambiguity_flags[]", "zero or more  →"),
    ]
    fh = (rec_top - 0.30 - rec_bot - 0.06) / len(fields)
    fy = rec_top - 0.30
    field_rows = {}
    for name, detail in fields:
        fy -= fh
        s.rect(col2_x + 0.06, fy + 0.02, col2_w - 0.12, fh - 0.04, WHITE, RULE, 0.4)
        s.text(col2_x + 0.12, fy + 0.02, 1.02, fh - 0.04, name, 6.2, True, INK, "left", "middle")
        s.text(col2_x + 1.14, fy + 0.02, col2_w - 1.20, fh - 0.04, detail, 5.9, False, INK, "left", "middle")
        field_rows[name] = (fy + fh / 2.0)

    # --- Column 3: controlled vocabularies
    def vocab(y0, h, title, items, fill):
        s.rect(col3_x, y0, col3_w, h, fill, RULE, 0.6)
        s.text(col3_x + 0.06, y0 + h - 0.19, col3_w - 0.12, 0.16, title, 6.6, True, INK, "left", "middle")
        s.text(col3_x + 0.06, y0 + 0.05, col3_w - 0.12, h - 0.26, items, 5.8, False, INK, "left", "top")

    v1_h, v2_h, v3_h = 1.02, 0.72, 1.30
    v1_y = y - v1_h
    vocab(v1_y, v1_h, "parse_status",
          "formula_parsed\nmixture_parsed\nsemantic_rule_extracted\nambiguous_rejected\nunsupported_rejected\nparse_error", BLUE)
    v2_y = v1_y - 0.14 - v2_h
    vocab(v2_y, v2_h, "component role",
          "host  ·  additive  ·  dopant\nalloying_species\nsolvent  ·  unknown", GREEN)
    v3_y = v2_y - 0.14 - v3_h
    vocab(v3_y, v3_h, "ambiguity_flags",
          "comma_site_fraction_missing\nunit_convention_missing\ncharge_balance_unspecified\nhydration_or_dot_notation\nunconsumed_separator\nunknown_element_symbol\nmanual_validation_required", AMBER)

    # --- Grounding arrows: examples -> record
    s.arrow(col1_x + col1_w, ax_y + ex_h / 2.0, col2_x, field_rows["raw_expression"], weight=0.9)
    s.path([(col1_x + col1_w, rj_y + ex_h / 2.0),
            (col2_x - 0.14, rj_y + ex_h / 2.0),
            (col2_x - 0.14, field_rows["parse_status"]),
            (col2_x, field_rows["parse_status"])], weight=0.9, color=ACCENT)

    # --- record -> vocabulary (dashed = "value drawn from this vocabulary")
    s.path([(col2_x + col2_w, field_rows["parse_status"]),
            (col3_x - 0.10, field_rows["parse_status"]),
            (col3_x - 0.10, v1_y + v1_h / 2.0),
            (col3_x, v1_y + v1_h / 2.0)], dashed=True, weight=0.8, color=RULE)
    s.path([(col2_x + col2_w, field_rows["  · role"]),
            (col3_x - 0.06, field_rows["  · role"]),
            (col3_x - 0.06, v2_y + v2_h / 2.0),
            (col3_x, v2_y + v2_h / 2.0)], dashed=True, weight=0.8, color=RULE)
    s.path([(col2_x + col2_w, field_rows["ambiguity_flags[]"]),
            (col3_x - 0.10, field_rows["ambiguity_flags[]"]),
            (col3_x - 0.10, v3_y + v3_h / 2.0),
            (col3_x, v3_y + v3_h / 2.0)], dashed=True, weight=0.8, color=RULE)

    s.text(col1_x, 0.22, col1_w, 0.82,
           "Grounding relation: each raw string is bound to typed record slots. "
           "Solid arrows carry the two example strings into the record; dashed links "
           "mark slots whose value is constrained to a controlled vocabulary on the right.",
           5.9, False, RULE, "left", "top")

    s.save("paper2_schema_grounded")


def main() -> None:
    app = vc.open_visio()
    try:
        build_pipeline(app)
        build_schema(app)
    finally:
        app.Quit()


if __name__ == "__main__":
    main()
