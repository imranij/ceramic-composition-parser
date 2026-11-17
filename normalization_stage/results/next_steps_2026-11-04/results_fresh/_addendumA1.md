
## Addendum A (4 November 2026): guard for the failure cause, and a fresh held-out test

### A1. Pre-registration (written and committed before the fresh set is scored)

**Fix.** H2b is the frozen H2 stage (`composition_normalise.py`, unchanged) plus a guard in a new file,
`package_copy/code/composition_normalise_guarded.py`. The guard runs only on strings that H2 resolved after v0.2.0
refused them. G1 refuses a residual formula with no digit and four or more elements (element-list signature).
G2 refuses an oxygen-bearing composition when no assignment of the cations' known oxidation states (union of
pymatgen's common and ICSD states, mixed valence allowed, oxygen at -2) balances the charge within 2% of the
oxygen charge. A refused string keeps its original v0.2.0 refusal.

**Design attempts, development release only.**

| attempt | data | H2-rescued strings | refused by guard | effect on determinate agreement |
|---|---|---|---|---|
| G1 + G2, no tolerance | dev half | 154 | 4: `α-SiAlON`, `β-SiAlON` (G1); `Potassium titanate K0.8Ti1.73Li0.27O4`, `titanium oxide Cs0.67Ti1.83O4` (G2) | 3,474 to 3,470 |
| G2 tolerance 2% of oxygen charge (the two titanates balance to 7.99 against 8) | dev half | 154 | 2: the two SiAlON strings | 3,474 to 3,472 |
| same, frozen candidate | dev-test half (1 of at most 2) | 145 | 1: `Lu2RuO7(s)` (G2) | 3,413 to 3,412 |

No change was made after the dev-test scoring. Synthetic checks: `NiMoO oxide`, `CeLaO oxide`,
`LaSrCoFeO oxide` and `SiAlON ceramics` are refused; `BiOCl nanosheets`, `LaOF powder`, `TiO powder`,
`Fe3O4 MNPs`, `Pb3O4 powder` and layered Li-rich oxides are kept; `BaO2 powder` (peroxide) is refused, which is a
known cost. A known gap: shorthand that happens to balance, such as a hypothetical `TiZrO2 oxide`, passes.
Frozen SHA-256 values are in `H2b_FROZEN_before_fresh.sha256` (H2 file 1b06a5a4...163d12; guard file
4577aa0f...36e858; 2026-11-04T10:26:44Z).

**Fresh held-out set.** The project trees hold no unused pool of target strings: every unique target string of
both Kononova releases is already in the development set (19,443) or the sol-gel held-out set (3,524). The same
two releases (SHA-256 checked) also carry `precursors[].material_string`, a field neither earlier set used, with a
composition assigned by the same Ceder-group pipeline. The fresh set is the census of unique precursor strings
that occur in neither earlier set: 5,555 strings from 3,942 first DOIs (3,277 first seen in the solid-state
release, 2,278 in the sol-gel release). No sampling was needed, so no seed applies. Reference classes, computed
by the unchanged `reference_class` before any parser ran: 3,452 determinate, 1,879 mixture (mostly hydrates
such as `Fe(NO3)3·9H2O`), 224 indeterminate. Builder: `scripts/build_fresh_pool.py`; pool:
`results_fresh/fresh_pool_precursor_strings.csv`. Caveats stated now: precursor strings come from the same
papers as the targets (DOIs overlap with both earlier sets), so the unit of independence is the string and the
DOI-level test is again a sensitivity analysis; and precursors are mostly simple reagents, so the headroom may be
smaller than for targets. Baseline outcomes on the fresh set were not computed before this registration.

**Decision rule for H2b (all three must hold; thresholds scaled to 3,452 determinate strings).**
1. Determinate agreement of H2b minus that of raw pymatgen is at least ceil(0.03 x 3,452) = 104 strings
   (3.0 points), and minus that of pymatgen plus element check (`v01_guarded`) is at least 104 strings.
2. Exact two-sided McNemar test on paired strings, endpoint determinate agreement, p < 0.05 against both.
3. Zero wrong reads among the hand-checked rescued strings (H2b resolves, v0.2.0 refuses): all of them if 200 or
   fewer, otherwise a random 200 drawn with seed 20261104 plus every rescued string that is reference-discordant.
   Wrong read has the same definition as in section 1.

One scoring run. The unguarded H2 stage is scored in the same run as a secondary comparison only. The rescued
strings go to a third annotation sheet for the same two annotators; the 304-string sheets are not changed.
