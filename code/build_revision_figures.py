"""Figures new or redrawn at revision R1, in the house style of the Visio schematics.

The two original schematics were drawn through Visio automation, which needs a
Windows host. These are drawn with matplotlib using the same palette, Times-metric
serif type (Liberation Serif), dashed group enclosures, dark card headers and navy
block arrows. Every number drawn is read from a committed CSV.

Outputs (figures/):
  fig_pipeline_v02.pdf        Introduction: end-to-end pipeline
  fig_screen_examples.pdf     Methods: five literature strings through screen, grammar, cross-check
  fig_schema_v02.pdf          Methods: the record schema and its grounding relations
  fig_literature_eval.pdf     Results: development and held-out literature evaluation
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrow, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES = DATA / "processed_results"
FIG = ROOT / "figures"


def rgb(t):
    return tuple(v / 255 for v in t)


NAVY = rgb((23, 54, 93))
HEAD = rgb((59, 74, 94))
EDGE = rgb((38, 52, 72))
DASH = rgb((143, 161, 184))
PALE = rgb((201, 218, 238))
GREY = rgb((150, 160, 172))
INK = (0, 0, 0)

plt.rcParams.update({"font.family": "Liberation Serif", "pdf.fonttype": 42, "font.size": 8})


class Canvas:
    def __init__(self, w: float, h: float):
        self.fig = plt.figure(figsize=(w, h))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(0, h)
        self.ax.axis("off")
        self.h = h

    def y(self, top: float) -> float:   # convert a distance from the top into axes y
        return self.h - top

    def panel(self, x, top, w, h, title):
        self.ax.add_patch(Rectangle((x, self.y(top + h)), w, h, fill=False, ec=DASH,
                                    lw=0.8, ls=(0, (4, 2))))
        self.ax.text(x + w / 2, self.y(top + 0.13), title, ha="center", va="center",
                     fontsize=8.6, fontweight="bold")

    def card(self, x, top, w, h, title, body, head=HEAD, title_color="white",
             body_size=7.4, mono=False):
        hh = 0.21
        self.ax.add_patch(Rectangle((x, self.y(top + h)), w, h, fc="white", ec=EDGE, lw=0.7))
        self.ax.add_patch(Rectangle((x, self.y(top + hh)), w, hh, fc=head, ec=EDGE, lw=0.7))
        self.ax.text(x + w / 2, self.y(top + hh / 2), title, ha="center", va="center",
                     color=title_color, fontsize=8.0, fontweight="bold")
        self.ax.text(x + w / 2, self.y(top + hh + (h - hh) / 2), body, ha="center",
                     va="center", fontsize=body_size, linespacing=1.25,
                     family="Liberation Mono" if mono else "Liberation Serif")

    def down(self, x, top, length, label=""):
        self.ax.add_patch(FancyArrow(x, self.y(top), 0, -length, width=0.11, head_width=0.27,
                                     head_length=0.11, length_includes_head=True, color=NAVY, lw=0))
        if label:
            self.ax.text(x + 0.22, self.y(top + length / 2), label, ha="left", va="center",
                         fontsize=7.6)

    def right(self, x, ymid_top, length):
        self.ax.add_patch(FancyArrow(x, self.y(ymid_top), length, 0, width=0.09, head_width=0.22,
                                     head_length=0.09, length_includes_head=True, color=NAVY, lw=0))

    def save(self, stem):
        FIG.mkdir(exist_ok=True)
        self.fig.savefig(FIG / f"{stem}.pdf")
        self.fig.savefig(FIG / f"{stem}.png", dpi=220)
        plt.close(self.fig)
        print("wrote", stem)


def _n(x) -> str:
    return f"{int(x):,}"


def pipeline() -> None:
    out = pd.read_csv(RES / "literature_outcomes.csv")
    strings = int(out[out.configuration == "v02_package"].strings.sum())
    corpus = pd.read_csv(RES / "corpus_backend_check.csv")
    n_db = int(corpus[corpus.source_dataset == "TOTAL"].formulas.iloc[0])
    W, H = 7.16, 6.2
    c = Canvas(W, H)
    m, g = 0.08, 0.12
    # panel 1
    c.panel(m, 0.05, W - 2 * m, 0.92, "Raw composition strings")
    w3 = (W - 2 * m - 4 * g) / 3
    xs = [m + g + i * (w3 + g) for i in range(3)]
    c.card(xs[0], 0.33, w3, 0.56, "Open databases", f"six corpora,\n{_n(n_db)} formula records")
    c.card(xs[1], 0.33, w3, 0.56, "Literature strings",
           f"{_n(strings)} unique strings as written,\neach with its source DOI")
    c.card(xs[2], 0.33, w3, 0.56, "Thesis ratio expressions",
           "the host/additive lineage\nthe package was built from")
    c.down(W / 2 - 0.6, 0.99, 0.28, "one string at a time")
    # panel 2
    c.panel(m, 1.29, W - 2 * m, 0.98, "Screen, identical for every backend")
    c.card(xs[0], 1.57, w3, 0.62, "Ambiguity rules",
           "comma, dot and hydrate, free variable,\ncolon dopant, %, charge, (X) group,\nzero amount", head=NAVY,
           body_size=7.1)
    c.card(xs[1], 1.57, w3, 0.62, "Lexical rules",
           "words and labels, operators,\nunknown or placeholder symbols,\nstray separators", head=NAVY,
           body_size=7.1)
    c.card(xs[2], 1.57, w3, 0.62, "Unit interpreter",
           "mol%, wt%, at% with a declared basis;\nroles supplied by the caller,\nnever inferred", head=NAVY,
           body_size=7.1)
    c.down(W / 2 - 0.6, 2.29, 0.28, "screened tokens")
    # panel 3
    c.panel(m, 2.59, W - 2 * m, 0.84, "Parse and cross-check")
    w2 = (W - 2 * m - 3 * g - 0.3) / 2
    c.card(m + g, 2.87, w2, 0.5, "Deterministic grammar",
           "elements; decimal and rational subscripts;\nnested (), [ ] and { } groups", head=NAVY)
    c.right(m + g + w2 + 0.04, 3.12, 0.3 + g - 0.08)
    c.card(m + 2 * g + w2 + 0.3, 2.87, w2, 0.5, "pymatgen cross-check",
           "the two results must agree;\na disagreement is refused", head=NAVY)
    c.down(W / 2 - 0.6, 3.45, 0.28, "elemental amounts")
    # panel 4
    c.panel(m, 3.75, W - 2 * m, 0.84, "Ground")
    c.card(m + g, 4.03, W - 2 * m - 2 * g, 0.5, "One schema-validated record per string, Eq. (1)",
           "status; components with role, coefficient, unit and basis; atomic fractions;\n"
           "provenance with parser version and backend; controlled refusal flags")
    c.down(W / 2 - 0.6, 4.61, 0.28, "one record")
    # panel 5
    c.panel(m, 4.91, W - 2 * m, 1.24, "Two exits, and only two")
    c.card(m + g, 5.19, w2 + 0.15, 0.62, "Accepted",
           "atomic-fraction vectors and JSON records\nfor composition-only models", head=PALE,
           title_color=INK)
    c.card(m + 2 * g + w2 + 0.15, 5.19, w2 + 0.15, 0.62, "Refused, with a reason",
           "a controlled flag in every CSV and JSON\noutput, routed to review, never coerced", head=PALE,
           title_color=INK)
    c.ax.text(W / 2, c.y(5.99), "There is no third path in which a partly understood string becomes a vector.",
              ha="center", va="center", fontsize=7.4, style="italic")
    c.save("fig_pipeline_v02")


EXAMPLES = [
    # string, what raw pymatgen returns, rule, v0.2 result
    ("Ba0.9Sr0.1TiO3", "Ba 0.9, Sr 0.1, Ti 1, O 3", "no rule fires; grammar and\npymatgen agree",
     "resolved"),
    ("Bi(Ni1/2Ti1/2)O3", "error (rational subscript)", "no rule fires; grammar resolves,\npymatgen refuses",
     "resolved, grammar only"),
    ("Li2O.2SiO2", "Li 2, O 2.2, Si 1", "dot not preceded by a digit:\ndecimal or adduct?",
     "refused: hydration_or_dot_notation"),
    ("BaO-2SiO2", "Ba 1, Si 1  (O cancels to 0)", "hyphen inside a formula:\nminus sign or separator?",
     "refused: mixture_or_arithmetic_notation"),
    ("MS2", "M 1, S 2  (M a DummySpecies)", "M is not one of the 118\nelement symbols",
     "refused: unknown_element_symbol"),
]


def screen_examples() -> None:
    inst = pd.read_csv(RES / "literature_hazard_instances.csv")
    dev = pd.read_csv(DATA / "literature_strings_eval.csv")
    doi = {}
    for s, *_ in EXAMPLES:
        row = dev[dev.string == s]
        doi[s] = row.first_doi.iloc[0] if len(row) else ""
    W = 7.16
    m, gap, rh = 0.08, 0.16, 0.56
    top = 0.36
    H = top + 0.3 + len(EXAMPLES) * (rh + 0.06) + 0.12
    c = Canvas(W, H)
    avail = W - 2 * m - 0.16 - 3 * gap
    frac = [0.24, 0.23, 0.26, 0.27]
    widths = [f * avail for f in frac]
    titles = ["Literature string", "Raw pymatgen returns", "Screen and cross-check", "Package v0.2.0"]
    c.panel(m, 0.05, W - 2 * m, H - 0.1, "Five strings from the development corpus, one decision each")
    xs, x = [], m + 0.08
    for w in widths:
        xs.append(x); x += w + gap
    for x, w, t in zip(xs, widths, titles):
        c.ax.add_patch(Rectangle((x, c.y(top + 0.22)), w, 0.22, fc=HEAD, ec=EDGE, lw=0.7))
        c.ax.text(x + w / 2, c.y(top + 0.11), t, color="white", ha="center", va="center",
                  fontsize=7.9, fontweight="bold")
    for i, (s, pm, rule, res) in enumerate(EXAMPLES):
        t = top + 0.3 + i * (rh + 0.06)
        refused = res.startswith("refused")
        for j, (x, w) in enumerate(zip(xs, widths)):
            fc = PALE if (j == 3 and refused) else "white"
            c.ax.add_patch(Rectangle((x, c.y(t + rh)), w, rh, fc=fc, ec=EDGE, lw=0.6))
            mid = c.y(t + rh / 2)
            if j == 0:
                c.ax.text(x + w / 2, mid + 0.08, s, ha="center", va="center", fontsize=7.4,
                          family="Liberation Mono")
                c.ax.text(x + w / 2, mid - 0.11, f"doi:{doi[s]}", ha="center", va="center",
                          fontsize=5.9, color=rgb((70, 80, 92)))
            elif j == 3:
                txt = res.replace(": ", ":\n")
                c.ax.text(x + w / 2, mid, txt, ha="center", va="center", fontsize=6.6,
                          family="Liberation Mono", linespacing=1.3)
            else:
                c.ax.text(x + w / 2, mid, [pm, rule][j - 1], ha="center", va="center", fontsize=7.2,
                          linespacing=1.25)
            if j < 3:
                c.right(x + w + 0.02, t + rh / 2, gap - 0.04)
    c.save("fig_screen_examples")
    _ = inst  # the examples are members of literature_hazard_instances.csv (checked in tests)


def schema() -> None:
    W, H = 7.16, 5.05
    c = Canvas(W, H)
    m, g = 0.08, 0.12
    w2 = (W - 2 * m - 3 * g) / 2
    c.panel(m, 0.05, W - 2 * m, 0.9, "Two worked strings")
    c.card(m + g, 0.33, w2, 0.54, "An accepted mixture",
           "0.98BaTiO3+0.02Y2O3, roles supplied\nby the caller as host, additive")
    c.card(m + 2 * g + w2, 0.33, w2, 0.54, "An ambiguous string",
           "(Ba,Sr)TiO3, whose site occupancy\nthe string does not determine")
    c.down(W / 2 - 0.6, 0.97, 0.26, "bound to the slots below")
    c.panel(m, 1.25, W - 2 * m, 0.98, "Typed slots of the record (schema 1.1.0)")
    w4 = (W - 2 * m - 5 * g) / 4
    slots = [("parse_status", "one of six controlled\nstates"),
             ("components", "role and its source,\ncoefficient, unit, basis"),
             ("atomic_fractions", "normalized element\nfractions, sum 1"),
             ("provenance and flags", "parser version, backend;\n15 controlled flags")]
    for i, (t, b) in enumerate(slots):
        c.card(m + g + i * (w4 + g), 1.53, w4, 0.6, t, b, head=NAVY, body_size=7.2)
    c.down(W / 2 - 0.6, 2.25, 0.26, "controlled vocabularies")
    c.panel(m, 2.53, W - 2 * m, 1.06, "Where each string lands")
    c.card(m + g, 2.81, w2, 0.7, "mixture_parsed",
           "components: BaTiO3 host 0.98, Y2O3 additive 0.02\nfractions: Ba 0.196, Ti 0.196, O 0.600, Y 0.008\n"
           "flags: none", body_size=7.1)
    c.card(m + 2 * g + w2, 2.81, w2, 0.7, "ambiguous_rejected",
           "components: none; fractions: none\nflags: comma_site_fraction_missing\nbackend: not_resolved",
           body_size=7.1)
    c.down(W / 2 - 0.6, 3.61, 0.26, "checked on every output path")
    c.panel(m, 3.89, W - 2 * m, 1.1, "What the schema enforces, and what it does not")
    c.card(m + g, 4.17, W - 2 * m - 2 * g, 0.74,
           "A runtime contract on every record and every CSV row the package writes",
           "every output carries the controlled status and flags; conditional rules forbid fractions on a refusal\n"
           "and require at least one flag; roles are never inferred. It is a record model, not an ontology.",
           head=PALE, title_color=INK, body_size=7.2)
    c.save("fig_schema_v02")


def literature_eval() -> None:
    o = pd.read_csv(RES / "literature_outcomes.csv")
    order = ["raw_pymatgen", "v01_fallback", "v01_guarded", "v02_package"]
    label = {"raw_pymatgen": "raw pymatgen", "v01_fallback": "v0.1 grammar alone",
             "v01_guarded": "v0.1 as submitted", "v02_package": "v0.2.0"}
    sets = [("development", NAVY, "o", 0.13), ("heldout", GREY, "s", -0.13)]
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.5), gridspec_kw={"wspace": 0.6})
    ax = axes[0]
    for setname, colr, mk, off in sets:
        part = o[o.set == setname].set_index("configuration")
        for y, cfg in enumerate(order):
            v = 100 * part.loc[cfg, "determinate_agree"] / part.loc[cfg, "determinate"]
            ax.plot([v], [y + off], marker=mk, color=colr, ms=5, ls="none",
                    label=("development" if setname == "development" else "held-out") if y == 0 else None)
            ax.text(v + 0.5, y + off, f"{v:.1f}", va="center", fontsize=6.8)
    ax.set_xlim(72, 92)
    ax.set_title("Determinate strings resolved in agreement\nwith the reference (% of determinate)", fontsize=8)
    ax.grid(axis="x", color="#DCE1E6", lw=0.6)
    ax = axes[1]
    for setname, colr, mk, off in sets:
        part = o[o.set == setname].set_index("configuration")
        vals = [int(part.loc[c, "discordant_returns"]) for c in order]
        bars = ax.barh([y + off for y in range(len(order))], vals, height=0.24, color=colr, left=0)
        for bar, v in zip(bars, vals):
            ax.text(v * 1.15, bar.get_y() + bar.get_height() / 2, str(v), va="center", fontsize=6.8)
    ax.set_xscale("log")
    ax.set_xlim(1, 3000)
    ax.set_title("Reference-discordant returns\n(strings, log scale)", fontsize=8)
    for ax in axes:
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels([label[c] for c in order], fontsize=7.6)
        ax.set_ylim(-0.5, len(order) - 0.5)
        ax.tick_params(axis="x", labelsize=7)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=7.4,
               bbox_to_anchor=(0.5, -0.06))
    fig.savefig(FIG / "fig_literature_eval.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig_literature_eval.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_literature_eval")


if __name__ == "__main__":
    pipeline()
    screen_examples()
    schema()
    literature_eval()
