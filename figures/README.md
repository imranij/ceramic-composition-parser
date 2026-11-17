# Figures (revision R1, package v0.2.0)

| file | where | built by |
|---|---|---|
| fig_pipeline_v02.pdf | main Fig. 1 (Introduction) | code/build_revision_figures.py |
| fig_screen_examples.pdf | main Fig. 2 (Methods) | code/build_revision_figures.py |
| fig_schema_v02.pdf | main Fig. 3 (Methods) | code/build_revision_figures.py |
| fig_literature_eval.pdf | main Fig. 4 (Results) | code/build_revision_figures.py |
| paper2_element_coverage_origin_style.pdf, paper2_parser_coverage_by_dataset_origin_style.pdf, paper2_formula_complexity_origin_style.pdf | ESI Figs. S1 to S3 | code/build_data_figures.py |
| paper2_thesis_ratio_status_origin_style.pdf, paper2_thesis_mixture_atomic_fractions_origin_style.pdf | ESI Figs. S4, S5 | code/build_data_figures.py |
| paper2_pipeline_grounded.pdf, paper2_schema_grounded.pdf | not used (v0.1 schematics drawn in Visio; superseded by the two v0.2 schematics above, redrawn in the same house style with matplotlib) | Visio |

Every number drawn in a figure is read from a committed CSV. The history below
documents the earlier figure rebuild of the submitted version.

---

# Schematic figure rebuild — 12_Ontology_Grounded_Composition_Parsing

Rebuild of the schematic figures of `manuscript/main.tex`, against
`files/FIGURE_REBUILD_PROMPT.md`. Result plots were not touched.

Backup before any edit: `_figrebuild_backup_20260902-051539/` — the whole
`figures/` tree plus the pre-edit `main.tex`.

---

## 1. Class, options, measured widths

```
\documentclass[10pt,journal]{IEEEtran}
```

Probe compiled with those exact options:

| quantity | TeX pt | inches (pt / 72.27) |
|---|---|---|
| `\textwidth`   | 516.0 | **7.1400** |
| `\columnwidth` | 252.0 | 3.4870 |
| `\textheight`  | 696.0 | 9.6307 |

Two column. Both schematics are `figure*` floats spanning both columns at
`\textwidth`, included with `width=\textwidth`, scale exactly 1.000. That is the
wide regime: bands run left to right with one row of boxes each.

## 2. Classification of the existing figures

**Schematic — in scope (2):** `paper2_pipeline_grounded` (`fig:pipeline`) and
`paper2_schema_grounded` (`fig:schema`), both `figure*`.

**Result plots — left alone (5):** `paper2_element_coverage_origin_style`,
`paper2_parser_coverage_by_dataset_origin_style`,
`paper2_formula_complexity_origin_style`,
`paper2_thesis_ratio_status_origin_style`,
`paper2_thesis_mixture_atomic_fractions_origin_style`. All are corpus statistics
plotted from the parser outputs.

## 3. Which case applied

**Case B** — two schematics already existed. Neither was renumbered or
restructured; each keeps its role, label, filename and `figure*` float type.

## 4. What each figure uniquely shows

- **Fig. 1 `fig:pipeline`** — raw composition string to grounded record, and the
  only two exits the design allows.
- **Fig. 2 `fig:schema`** — the record model, where an accepted and an ambiguous
  string each land in it, and what the schema is not.

*How a string is processed* → *what the resulting record looks like, and what it
does not guarantee.* No overlap.

## 5. Concrete defects found in the originals

Unusually, **both figures were already the right size on the page**: drawn at
7.140 in and included at `\textwidth`, i.e. scale 1.0000. The defect was
entirely internal.

| | page (in) | drawn = printed (pt) | text shapes |
|---|---|---|---|
| `paper2_pipeline_grounded` | 7.140 × 4.160 | 5.7, 5.8, 5.9, 6.2, 6.6, 6.8, 6.9, 7.0 | 32, **all below 8 pt** |
| `paper2_schema_grounded` | 7.140 × 3.980 | 5.8, 5.9, 6.2, 6.4, 6.6, 6.8, 7.2 | 31, **all below 8 pt** |

**All 63 text shapes across the two figures printed below the 8 pt floor**, and
none reached it — the largest anywhere was 7.2 pt. Because the scale was 1.0,
this was not a shrink artifact: the type was authored that small.

Line weights compounded it: the schema figure had eight rules at **0.40 pt** and
three at 0.50 pt, against a 0.5 pt reproduction floor, and the pipeline figure
had twelve at 0.50 pt and thirteen at 0.60 pt.

Tonally both were `#e8eff7` against `#ffffff` — luminance 238 against 255, which
carries no separation once converted to grayscale.

Glyph coverage was clean in both: `·` (U+00B7), `φ`, `Σ`, `→` and the em dash are
all present in Times New Roman. Nothing had to be rewritten for that reason.

## 6. A caption that no longer matched its figure

Fig. 2's caption ended: *"The `parse_status`, component `role`, and
`ambiguity_flags` slots draw their values from the controlled vocabularies on
the right (dashed links)."* The rebuilt figure has no right-hand vocabulary
column and no dashed links — it states the controlled-vocabulary property inside
the `parse_status` box instead. The caption was cut to one line and its content
moved into referencing prose that describes what is actually drawn.

## 7. Sizes of the rebuilt figures

| figure | size (in) | float | scale | of `\textheight` | shapes |
|---|---|---|---|---|---|
| `paper2_pipeline_grounded` | 7.140 × 5.490 | `figure*` | 1.000 | 57 % | 83 |
| `paper2_schema_grounded` | 7.140 × 4.495 | `figure*` | 1.000 | 47 % | 65 |

Build reports **no fit warnings**. `validate_figs.py` passes both: 0 `Pos`
cells, 1 `Character` row, 1 `<cp>` run, `Style` in {0, 17}, `HorzAlign` 0,
Times New Roman throughout, every glyph in the face's cmap, both PDF fonts
embedded as `/FontFile2` subsets. Body 8 pt, headers 8.5 pt bold.

Literal underscores in the schema slot names (`parse_status`,
`ambiguous_rejected`) are written with figlib's `\_` escape, because a bare
underscore is subscript markup in the text emitter.

Semantics: the three validation checks in Fig. 1 are drawn **without** arrows
between them, because each is an independent guard on the same parsed formula
rather than a stage feeding the next; the two exits are drawn as alternatives
for the same reason; and the four record slots in Fig. 2 are parallel, not
sequential.

## 8. Equation-number mapping

| label | number | printed in |
|---|---|---|
| `eq:record` | **(1)** | Fig. 1, "Ground" band |

Read from `main.aux` after the final compile; declared once as `EQ_RECORD` in
`build_parser_figures.py`. It is the only equation number either figure prints.

## 9. Compile result

`pdflatex` → `bibtex` → `pdflatex` ×2:

- **10 pages**
- **0 errors**, **0 undefined references or citations**
- **0 overfull hboxes above 10 pt**
- `\begin{figure}` 7 / `\end{figure}` 7

| figure | number | page | referenced in |
|---|---|---|---|
| `fig:pipeline` | 1 | 3 | Section I |
| `fig:schema` | 2 | 5 | Section III-C |
| `fig:element_coverage` | 3 | 6 | |
| `fig:parser_coverage` | 4 | 6 | |
| `fig:formula_complexity` | 5 | 7 | |

Both schematics land near their references. Page 3 was rasterized and inspected:
the `figure*` spans both columns at the top of the page at scale 1.000, with
8 pt type reading correctly against the 10 pt IEEEtran body. No collisions, no
clipped text.

## 10. LaTeX changes made

- Fig. 1's caption was already one line and was kept. A paragraph was added
  explaining why the three validation checks and the two exits are drawn without
  arrows, and stating that the design deliberately has no third exit.
- `Eq.~\eqref{eq:record}` was doubling the label — `\eqref` already supplies the
  parentheses — so it now reads `\eqref{eq:record}`.
- Fig. 2's caption was cut from four sentences to one. Its substance moved into
  two paragraphs: what each of the two worked strings binds, and why the "target
  record model, not a validation contract" limitation is stated inside the figure
  rather than only in the text.

## 11. Judgment calls the author should check

1. **Fig. 2's final band carries the limitation in the figure.** The manuscript
   already sets this in bold in Section III-C; putting it in the figure is a
   presentational choice, made because a schema diagram showing controlled
   vocabularies otherwise implies a runtime contract the package does not yet
   provide.
2. **The right-hand controlled-vocabulary column with dashed links is gone**
   (Section 6). If that layout is wanted back, it needs re-adding to the builder
   and the caption restoring with it.
3. **Fig. 1 quotes "six corpora, 28 100 unique formulas"** from the abstract. The
   figure does not repeat the parse-rate statistics, because those are the
   subject of the result plots and Table IV.
4. `paper2_pipeline_grounded_tmp.vsdx` and `paper2_schema_grounded_tmp.vsdx` are
   leftovers of the earlier restyling pass and are stale. The `.svg` and `.png`
   siblings of both schematics are now out of date relative to the rebuilt
   `.pdf`/`.vsdx`; nothing in the manuscript includes them.

## 12. Files

| file | note |
|---|---|
| `build_parser_figures.py` | the builder; imports the shared `figlib` and `figkit` |
| `paper2_pipeline_grounded.{vsdx,pdf}` + `_preview.png` | Fig. 1 |
| `paper2_schema_grounded.{vsdx,pdf}` + `_preview.png` | Fig. 2 |
| `_vsdx_shell/` | unpacked OPC shell |

```
C:\ProgramData\Anaconda3\python.exe build_parser_figures.py
C:\ProgramData\Anaconda3\python.exe ..\..\_figure_style_tools\validate_figs.py . paper2_pipeline_grounded paper2_schema_grounded
```
