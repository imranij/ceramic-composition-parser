# Paper 12: name-stoichiometry guard (G3), design, freeze and post hoc diagnostic

Pre-registration: `PREREGISTRATION_G3_12.md`. Freeze: `G3_FROZEN.sha256` (G3 file 39d603ba...75728e; H2 and H2b files
unchanged, 1b06a5a4...163d12 and 4577aa0f...36e858; frozen 2026-11-04T20:07:33Z). Code:
`code/composition_normalise_g3.py`, to be placed next to `next_steps_2026-11-04/package_copy/code/`.

## 1. Design (development release only)

| check | data | H2-rescued strings | refused upstream by the H2b guard | refused by G3 |
|---|---|---|---|---|
| design | dev half | 154 | 2 | 0 |
| check 1 of 2 | dev-test half | 145 | 1 | 0 |
| notation benchmarks | `notation_benchmarks_scored.csv`, 51 rows | | | 0 changed |
| synthetic strings | 47 written by the designer (`g3_synthetic.py`) | | | 0 mismatches with the expected outcome |

The development release contains no string of the target class among its rescued strings: G3 had nothing to refuse
there, and it refused nothing that was right. The rules were therefore set from chemistry (fixed anion charges,
multiplicity prefixes, stated oxidation states) and checked on synthetic strings. The designer knew the four pool-2
wrong reads when writing the rules, which is why every held-out number below is post hoc. Logs:
`design_dev_log.txt`, `design_devtest_log.txt`, `synthetic_log.txt`, `benchmarks_log.txt`.

Known gaps from the synthetic checks: `vanadium pentoxide V2O5` and other `-pentoxide`, `-monoxide` names are not
stripped by the frozen H2 stage at all, so G3 never sees them; hydrates and acid salts are not judged; mixed
anions (`ammonium nitrate`) are not judged.

## 2. Search for a further unused pool

None exists (`POOL_SEARCH.md`). No clean held-out test of G3 was run, and none is claimed.

## 3. Post hoc diagnostic on the two spent pools (not a held-out test)

Script `g3_posthoc_diagnostic.py`; outputs in `posthoc/`. G3 never changes a string that v0.2.0 resolves.

| | pool 1, sol-gel targets | pool 2, fresh precursors |
|---|---|---|
| determinate strings | 1,403 | 3,452 |
| H2b agree | 1,167 (83.18%) | 1,732 (50.17%) |
| H2b + G3 agree | 1,167 (83.18%) | 1,728 (50.06%) |
| strings refused by G3 | 0 | 4 |
| wrong reads still returned, all hand-checked rescued strings | 0 of 3 (the H2b guard already refuses them) | 0 of 4 |
| wrong reads still returned, registered sample of 200 | | 0 of 3 |
| H2b + G3 vs raw pymatgen | +69; 4.92 points (3.28 to 6.59); 102 vs 33, p = 2.2e-9 | +229; 6.63 points (5.27 to 8.01); 314 vs 85, p = 5.8e-32 |
| H2b + G3 vs pymatgen + element check | +71; 5.06 points (3.34 to 6.76); 102 vs 31, p = 4.9e-10 | +309; 8.95 points (7.79 to 10.23); 314 vs 5, p = 5.1e-86 |
| H2b + G3 vs H2b | 0 vs 0 | 0 vs 4, p = 0.125 |
| new discordant returns vs v0.2.0 | 0 | 0 |

The four strings G3 refuses on pool 2 are exactly the four wrong reads: `aluminum nitrate [Al(NO3)2]`,
`cobalt hydroxide (Co(OH))2`, `strontium nitrate [Sr(NO3)]` (G3a) and `tantalum dioxide [Ta2O5]` (G3b). It refuses
none of the 299 rescued strings judged correct. The machine reference accepts all four, so measured agreement falls by
4 strings, the same pattern as the H2b guard on pool 1.

Reading. Because the rules were written with these four strings in view, this shows only that the guard does what it
was built to do on the cases that motivated it, and that it costs nothing on the other 299 rescued strings and on
the development release. It is not evidence about the wrong-read rate on unseen strings. That needs new strings, for
example a later text-mined release with both 2020 releases removed, or expert labels on strings no rule has seen.
