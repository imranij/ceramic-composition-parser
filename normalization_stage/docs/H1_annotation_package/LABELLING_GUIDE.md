# Labelling guide: what does a composition string determine?

Thank you for helping. You will label short strings that name a material, as they were written in published
synthesis papers. For each string you decide one thing: does the string, read on its own, fix one chemical
composition? If it does, you write that composition. The task takes about four to six hours for the main sheet
of 304 strings and about one hour for the optional second sheet of 67 strings.

## What you receive

- `annotation_sheet_part1_304_annotator_<A or B>.csv` (main sheet, required)
- `annotation_sheet_part2_H2_rescued_annotator_<A or B>.csv` (second sheet, optional but valuable)
- this guide

Work alone. Do not discuss strings with the other annotator until both sheets are returned. Do not run any
parser, script or language model on the strings. Open the sheet in Excel or LibreOffice, fill the four blank
columns, and save it as CSV (UTF-8) under the same name. Do not change the `item_id`, `string` or `first_doi`
columns, and do not reorder or delete rows.

## The four columns you fill

**decision**: exactly one of the three words below, in lower case.

- `determinate`: the string alone fixes one composition, that is, one set of elements with definite relative
  amounts. Examples: `BaTiO3`, `La0.7Sr0.3MnO3`, `Ba(Zn1/3Nb2/3)O3`, `spinel MgAl2O4` (the word does not change
  the composition), `α-Al2O3` (a polymorph label does not change the composition).
- `indeterminate`: the string does not fix a composition. Use this when there is a free variable (`x`, `y`,
  `δ`), a dopant or additive without an amount (`BaTiO3:Eu`, `Sr-doped LaMnO3`), a placeholder (`M`, `RE`, `Ln`),
  a percentage without a stated basis (mol%, wt% or at% not given, or the host not clear), a comma that shares a
  site without fractions (`(La,Sr)MnO3`), a dot that could be a decimal point or an adduct separator, a name with
  more than one common formula (`lithium silicate`), an abbreviation you cannot expand with certainty (`BNT`,
  `KNN`, `PZT` unless the amounts are stated), an element list rather than a formula (`NiMoO catalyst` meaning a
  Ni-Mo-O mixed oxide), or a string cut out of a longer formula (`(Ba0.5Sr0.5,`).
- `mixture`: the string fully specifies several components with numeric amounts, for example
  `0.9BaTiO3-0.1SrTiO3` or `Li2O·2SiO2` when you are sure the dot is an adduct separator. A mixture with any
  variable or unquantified part is `indeterminate`.

**composition**: only for `determinate` (and optionally for `mixture`, as the total over all components). Write
element:amount pairs separated by semicolons, for example `Ba:1;Ti:1;O:3` or `La:0.7;Sr:0.3;Mn:1;O:3`. Amounts can
be decimals or fractions (`Zn:1/3`). Any overall scale is fine (`Ba:2;Ti:2;O:6` equals `Ba:1;Ti:1;O:3`). Expand
groups (`Ca3(PO4)2` is `Ca:3;P:2;O:8`). Include hydrogen from water or ammonium if it is part of the formula.
Leave the cell empty for `indeterminate`.

**confidence**: 1 (guess), 2 (fairly sure), 3 (certain).

**note**: free text, optional. Say briefly why when you choose `indeterminate`, or when you were unsure.

## Rules for hard cases

1. Judge the string as written. The DOI is given so that you can look up an abbreviation or a word you do not
   know, but do not use the paper to fill in information the string leaves out. If the paper says x = 0.1 but
   the string says `La1-xSrxMnO3`, the string is `indeterminate`.
2. Words that describe structure, form or role (perovskite, spinel, garnet, oxide, powder, film,
   nanoparticles, MNPs, ceramic, glass, tetragonal, α-, β-, layered, n-type) do not change the composition.
   Words that change or qualify it do (doped, coated, loaded, supported, composite, deficient, rich, precursor,
   stabilised, with, and).
3. A chemical name together with a formula (`potassium niobate KNbO3`) is determinate if name and formula
   agree. If they disagree (`titanate BaZrO3`) choose `indeterminate` and say so in the note.
4. A name alone (`barium titanate`) is determinate only if there is one formula that any chemist would write
   for it. If two or more formulas are in common use, choose `indeterminate`.
5. A formula that is not charge-balanced in any plausible oxidation state usually signals shorthand. If you
   believe the string is a shorthand list of elements rather than a stoichiometry, choose `indeterminate`.
6. Crystallographic uncertainties in parentheses (`Sr1.97(1)`) are not part of the amount: write 1.97.
7. A state label (`(s)`, `(l)`) and stray punctuation from the surrounding sentence (a trailing comma or a
   dangling bracket, as in `(SrTiO3,`) do not change the composition.
8. If you cannot decide between two readings, choose `indeterminate` and write both readings in the note.

## When you finish

Return the filled CSV file(s) to Imran. Do not return the guide. The two sheets are compared item by item.
Items on which the two annotators differ are resolved afterwards by a third person or by discussion, without
changing your original sheets.
