
### A2. What was run

`scripts/fresh_score_once.py` checked both SHA-256 values and scored the 5,555 fresh strings once, on
2026-11-04 after the pre-registration above was committed. It scored raw pymatgen, `v01_guarded`, v0.2.0, the
unguarded H2 stage (secondary) and H2b. The log is `results_fresh/fresh_run_log.txt`. No setting was changed after
the run. The hand check covered the registered random sample of 200 of the 303 rescued strings (seed 20261104).
All 303 were also read, and the extra finding is reported separately. No rescued string was reference-discordant.

### A3. Results, with the first run side by side

Determinate agreement, with 95% DOI-cluster bootstrap intervals for the paired difference (4,000 resamples).

| | first run: H2 on sol-gel held-out targets | this run: H2b on fresh precursor strings |
|---|---|---|
| determinate strings | 1,403 | 3,452 |
| raw pymatgen agree | 1,098 (78.3%) | 1,499 (43.4%) |
| pymatgen + element check agree | 1,096 (78.1%) | 1,419 (41.1%) |
| v0.2.0 agree | 1,099 (78.3%) | 1,429 (41.4%) |
| stage agree | 1,170 (83.4%) | 1,732 (50.2%) |
| rule 1 threshold | 43 | 104 |
| gain over raw pymatgen | +72; 5.13 points (3.51 to 6.82) | +233; 6.75 points (5.35 to 8.15) |
| gain over pymatgen + element check | +74; 5.27 points (3.52 to 6.99) | +313; 9.07 points (7.89 to 10.34) |
| McNemar vs raw pymatgen (strings; DOIs) | 105 vs 33, p = 6e-10; 94 vs 32, p = 3e-8 | 318 vs 85, p = 9e-33; 227 vs 61, p = 1e-23 |
| McNemar vs pymatgen + element check | 105 vs 31, p = 1e-10 | 318 vs 5, p = 3e-87 |
| new discordant returns vs v0.2.0 | 0 | 0 |
| rescued strings | 71, all agree with the reference | 303, all agree with the reference |
| hand-checked | all 71 | registered sample of 200 |
| wrong reads | 3 of 71, 4.2% (1.4 to 11.7) | 3 of 200, 1.5% (0.5 to 4.3) |
| hazard behind the wrong reads | element-list shorthand (`CeZrO2 oxide`) | name contradicts formula (`strontium nitrate [Sr(NO3)]`) |
| rule 1 / rule 2 / rule 3 | pass / pass / fail | pass / pass / fail |

On the fresh set the guard refused 3 strings that the unguarded stage returned: `Na2O1.14(1)`,
`magnesium carbonate [Mg(CO3)2]` and `strontium nitrate Sr(NO3)3`. All three agree with the reference. The last two
are formulas that contradict their own names, so the refusals look right by hand check, but they lower measured
agreement by 3 strings (McNemar 0 vs 3, p = 0.25). No element-list string appeared among the fresh rescued strings.
So this run shows the guard does no harm, but it is weak evidence that the guard works on its target class.

The three wrong reads in the registered sample are `strontium nitrate [Sr(NO3)]`, `tantalum dioxide [Ta2O5]` and
`cobalt hydroxide (Co(OH))2`. In each one the stripped name fixes a stoichiometry that the formula contradicts.
Under the labelling guide (rule 3) such a string does not determine one composition. The stage removes the name
because it only checks that the name's elements occur in the formula. It does not check the counts. The machine
reference accepts all three, as it accepted the element-list cases. A fourth case lies outside the sample,
`aluminum nitrate [Al(NO3)2]`, which makes 4 of 303 overall (1.3%, 0.5 to 3.3). One more read is faithful to an
implausible formula (`MnO3 oxide`, probably an author typo). It is not counted as a wrong read. All 303 are in
`results_fresh/fresh_rescued_handchecked.csv`, with the sample marked.

Headroom on the fresh set is large: 1,938 determinate strings are agreed by neither v0.2.0 nor pymatgen. Most are
hydrate and reagent-grade strings, and names without formulas, which the stage refuses by design.

### A4. Outcome of Addendum A

H2b fails under its pre-registered rule, as H2 did, because rule 3 requires zero wrong reads. The agreement gain
replicates on a second set that shares no string with either earlier set. It is larger in points, and it adds no
new reference-discordant return. The fix removed the hazard it targeted, as far as this set can show. The
wrong-read rate fell from 4.2% to 1.5%, and its cause changed to a second, narrower hazard: names whose
stoichiometry contradicts the formula. The paper's position is stronger. The stage is a measured coverage gain
with a known residual hazard. It is not a validated component. Status for the route: PROGRESS.

What would come next, if wanted. A name-formula consistency check would refuse a stripped class word when its
fixed polyanion charge (nitrate -1, carbonate -2, hydroxide -1, phosphate -3) or multiplicity prefix (di-, tri-,
pent-) contradicts the formula. It should be designed on the development set. Both reference-labelled pools of
these releases are now used, so a third test could only come from the expert labels (part 3 of the annotation
package), or from a further text-mined release. That is a judgement call for Imran, not a step taken here.

### A5. Files added on 4 November

The pre-registration is section A1 above. Also added:
- `H2b_FROZEN_before_fresh.sha256`
- `package_copy/code/composition_normalise_guarded.py`
- `scripts/guard_design.py`, `scripts/build_fresh_pool.py`, `scripts/fresh_score_once.py`
- `results_fresh/` (pool, outcomes, McNemar, rescued with hand check, strings refused by the guard, all strings,
  run log)
- `H1_annotation_package/annotation_sheet_part3_fresh_rescued_annotator_A.csv` and `_B.csv`
- an extended key and analysis script (H2b as a fifth parser; the part 1 sheets are unchanged)
