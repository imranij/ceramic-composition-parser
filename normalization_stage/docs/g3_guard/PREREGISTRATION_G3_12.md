# Paper 12: pre-registration of the name-stoichiometry guard (G3), written 4 November 2026 (UTC) for the 5 November revision

Written before any G3 code was run on any string. Nothing in `next_steps_2026-11-04/`, `revision_R1/` or `source/`
is changed; all G3 files live in `revision_2026-11-05/g3_guard/`.

## Status of the evidence before this step

- Held-out pool 1 (sol-gel targets, 1,403 determinate) was used by H2 on 3 November.
- Held-out pool 2 (fresh precursor strings, 3,452 determinate) was used by H2b on 4 November.
- The failure cause G3 targets was found on pool 2: 3 wrong reads in the registered sample of 200 rescued strings
  (`strontium nitrate [Sr(NO3)]`, `tantalum dioxide [Ta2O5]`, `cobalt hydroxide (Co(OH))2`) and a fourth outside the
  sample (`aluminum nitrate [Al(NO3)2]`). The designer of G3 has seen these strings. Any G3 result on pool 1 or
  pool 2 is therefore post hoc and is reported only as a diagnostic.

## What G3 is

G3 is an extra check on top of the frozen H2b stage (`composition_normalise.py` SHA-256 1b06a5a4...163d12 and
`composition_normalise_guarded.py` SHA-256 4577aa0f...36e858, both imported unchanged). It runs only on strings that
H2b resolved after v0.2.0 refused them. When a stripped descriptor names a compound, G3 derives the stoichiometry or
oxidation state the name implies and refuses the string, keeping the original v0.2.0 refusal, if the bracketed or
attached formula contradicts it. Three sub-rules:

- G3a, fixed-charge anion salts. The stripped words contain exactly one anion class word without a prefix
  (nitrate, carbonate, hydroxide, sulfate or sulphate, phosphate, fluoride, chloride, bromide, iodide), and no
  `ammonium`. The oxyanion's own oxygen count must be met (for example O >= 3N for nitrate); extra oxygen counts as
  oxide. The named and unnamed cations, at the oxidation states a trivial name implies (pymatgen common oxidation
  states, mixed valence allowed between the lowest and highest), must balance the anion charge within 2%.
  Formulas with hydrogen outside a hydroxide are not judged (hydrates and acid salts).
- G3b, multiplicity prefix. A binary anion word with a multiplicity prefix (di-, tri-, tetra-, penta-, hexa-,
  hepta-, octa-, deca-) on a binary formula: the anion count as written, or the anion-to-cation ratio, must equal the
  prefix number.
- G3c, stated oxidation state. A Roman numeral after an element name, or ferric, ferrous, cupric, cuprous, stannic or
  stannous, fixes that element's state in the charge balance of G3a, or, for an oxide without a fixed-charge anion
  word, in the oxygen balance (other cations: pymatgen common and ICSD states, as in G2).

## Design and freeze

- Design data: the development release only (dev half for design, dev-test half for at most two checks).
- Allowed design evidence besides the corpus: synthetic strings written by the designer.
- Stop condition for design: G3 changes no development outcome that the reference marks as agreement, unless a
  hand check shows the change is a correct refusal; and G3 changes no outcome on the three notation benchmarks.
- Freeze: SHA-256 of `composition_normalise_g3.py`, written to `G3_FROZEN.sha256` before any scoring of either
  held-out pool.

## Search for a further unused pool, and what happens if one exists

Before freezing, the project tree (`submission in progress/12_Ontology_Grounded_Composition_Parsing`, read-only) and
the paper folder are searched for literature strings with a reference composition that appear in none of the
development set, held-out pool 1 and held-out pool 2. If such a pool exists, it is scored once under the same three
rules as Addendum A (gain >= 3.0 points of its determinate strings over raw pymatgen and over pymatgen with the
element check; exact McNemar p < 0.05 against both; zero wrong reads in a hand check of all rescued strings, or a
seed-20261105 random 200 plus every reference-discordant one). If no such pool exists, no clean test is claimed.

## Diagnostic runs after the freeze (post hoc, labelled so in every output)

1. Fresh precursor set (pool 2): rescue count, wrong reads among the registered 200 and among all 303 rescued
   strings, strings refused by G3, and determinate agreement with paired McNemar against raw pymatgen,
   `v01_guarded` and H2b.
2. Sol-gel held-out set (pool 1): the same counts, with the 71-string hand check.
No threshold is attached to these runs, and no decision depends on them.
