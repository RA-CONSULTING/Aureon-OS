# Maeshowe repair and conditional controls v1

Frozen before the Isambard control run. The original scripts remain unchanged and are included by their Git content IDs and SHA-256 hashes. This is a software/model experiment. No measured twig counts or RTI files are supplied.

The repaired reader uses the medieval 16-character alphabet with 6:5:5 grouping, following Barnes, *Runic Tradition in Orkney*, printed p. 5, note 1. The source is https://www.arild-hauge.com/PDF/Barnes_Orkney_2003_pp_4-17.pdf . Group order and which side supplies the group number are explicit. Alternatives are never ranked against desired words, frequencies or coherence. A 24-character comparison preset is separately named; it cannot be silently used as a medieval reading.

Input example, purely synthetic: group on left, reverse order, left 2/right 1 yields candidate h. Observed left 3/right 1 would yield f under that convention, whereas the original program's forward 24-character table yields t. No branch counts for Maeshowe 15 are presently observed. Empty observations stay empty.

## Original model reproduction

Load both frozen sources. Require matching numerical baseline after removing timestamps. Require the original baseline gamma 0.493163 and master beat 29.2832 Hz; report the paper's differing values separately. Enumerate all 24 original pivot assignments as counterfactuals. Do not alter the 0.945 threshold to make an outcome pass.

## Complete conditional comparison

Hold fixed the original nine completed rune assignments and four incomplete entries, the 13-entry wall population, original frequency vocabulary, gamma formula, rounding and selection of the nearest of seven Schumann targets. The nine completed runes are distinct. Their wall counts are NE=3, NW=1, SW=2, SE=3. Enumerate every allocation of these nine runes to these wall counts: 9!/(3!1!2!3!) = 5,040 allocations. Each represents 72 within-wall permutations and therefore has equal weight under uniform permutation of the nine selected runes.

For each of the 24 permutations of the four wall frequencies, evaluate all 5,040 allocations, yielding 120,960 equally weighted configurations. Include the actual configuration in the finite reference population. Save all gamma, phi-count and Schumann-distance outcomes, with the configuration indices and input hashes. Also save the gamma and phi-count distributions under the original wall-frequency mapping (5,040 configurations).

Report exact fractions with gamma or phi count greater than or equal to the baseline; for Schumann distance use less than or equal. These are conditional randomisation ranks, not population probabilities that the historical hypothesis is true. The baseline's rune selection, phi amplitude modulation and selection of inscriptions were not independently preregistered. This experiment cannot account for every historical researcher choice or establish archaeological intent. Do not use a favourable rank as confirmation.

## Phi amplitude ablation

Re-evaluate the original completed rune-to-wall assignments with all three amplitude factors set to 1. Keep the golden-ratio detection targets and other rules fixed. This is a model sensitivity comparison, not a new archaeological null. Check that the reimplementation exactly reproduces the original rounded score and frequencies before evaluating the ablation.

## Geometry check

Recompute the spherical bearing and distance from the paper's explicit coordinates using radius 6371.0088 km. This does not rerun the unavailable calendar-wheel code or establish a historical connection. The proposed polar-location and full-bearing historical tests remain pending original transformations and data.

## Verification and resources

Run 12 meaningful reader tests, baseline equality across source versions, independent aggregation versus the original, exact 5,040 and 120,960 coverage, finite outputs, bounds and baseline inclusion. Save raw outcomes in CSV, summary JSON, scheduler receipt, environment and hashes. Use one CPU allocation (four CPUs, 4 GB, maximum ten minutes); no GPUs requested. No expansion of this small finite calculation is useful. Stage corrected research software in a new directory in the existing isolated worktree; no original paper edit or publication.
