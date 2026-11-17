# Pre-registration, paper 12, hypothesis H2 (descriptor-word and punctuation stripping stage)

Written on 3 November 2026, before any design work on the development strings and before the held-out set is
scored with the new stage. It is not changed after the results are seen.

## Hypothesis

A pre-parse normalisation stage that removes descriptor words from a closed lexicon of material labels
(for example perovskite, ferrite, spinel, oxide, nanoparticles, NPs, MNPs, powder, film) and stray
punctuation (a trailing comma, an unmatched leading bracket), and then passes the residual string through the
unchanged v0.2.0 lexical screen, grammar and pymatgen cross-check, recovers determinate strings that v0.2.0 and
pymatgen both refuse. Every string it touches carries a controlled normalisation flag. It never overrides a
refusal flag that the residual string still triggers.

## Prediction with a size

On the 1,403 determinate held-out sol-gel strings, the configuration v0.2.0 plus the stripping stage
(`v03_strip`) agrees with the reference on at least 3.0 percentage points more strings than raw pymatgen,
that is on at least 1,098 + 43 = 1,141 strings (43/1,403 = 3.06 points). The upper bound of the gain is the
158 "other"-stratum determinate strings that both parsers refuse (11.3 points).

## Decision rule (all must hold for PASS of H2)

1. Held-out determinate agreement of `v03_strip` minus that of raw pymatgen is at least 43 strings (3.0
   points), and minus that of pymatgen plus element check (`v01_guarded`, 1,096) is at least 43 strings.
2. Exact two-sided McNemar test on paired held-out strings, endpoint determinate agreement, p < 0.05 against
   raw pymatgen and against `v01_guarded`. The DOI-level version (a DOI flagged if any of its strings is) is
   reported as a sensitivity analysis and does not enter the decision.
3. No new wrong reads. The rescued set is every held-out string that `v03_strip` resolves and v0.2.0 refuses.
   Every rescued string is checked by hand (all of them if there are 200 or fewer, otherwise a seeded random
   200 plus every rescued string that is reference-discordant). A wrong read is a returned composition that the
   string, read by a chemist, does not determine, or that differs from what it determines. The rule requires
   zero wrong reads in the hand-checked set. A rescued string whose reference disagrees but whose hand check
   finds the reference at fault is reported separately and is not counted as a wrong read.

If rule 1 or 2 fails, H2 fails. If rule 3 fails, H2 fails whatever the gain.

## Protocol and number of attempts

- Design uses only the development set (19,443 solid-state strings). It is split by the existing DOI hash
  column `split`: the lexicon and rules are built on `split == dev` strings, and checked on `split == test`
  development strings. At most three design iterations are scored on the development `test` half. All are
  reported.
- The stage is then frozen (SHA-256 of the source file recorded) and the held-out set is scored once. There is
  one held-out attempt. No change is made after it.
- Baselines are not changed: raw pymatgen 2026.5.4 (pymatgen-core 2026.8.30), and v0.1.0 with pymatgen
  preferred (pymatgen plus element-symbol check). Their outcomes are re-run in a fresh container and must
  reproduce the released columns exactly before the new stage is scored.
- The reference, the test strings and the agreement tolerance (1e-3 in atomic fraction) are unchanged.

## Disclosure of prior exposure to held-out strings

Before design, a few held-out strings were already seen, through the triage memo and a file header:
`Perovskite La0.8Sr0.2MnO3`, `Mn0.6Zn0.4Fe2O4 MNPs`, `(BiFeO3,`, `(β-Ca3(PO4)2,`,
`BiFe0.93Mg0.03Mn0.04O3,`, `La(M,Pd)O3`, and `Delafossite CuFeO2 oxide` (annotation sample). The lexicon
words in them (perovskite, MNPs, oxide, delafossite) were also named in the task brief. No other held-out
strings are inspected before the held-out run.
