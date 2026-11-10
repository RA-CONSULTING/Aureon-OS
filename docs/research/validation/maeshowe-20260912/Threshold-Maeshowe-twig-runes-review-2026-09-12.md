# People of the Threshold, Maeshowe and the twig runes

Research review — 12 September 2026

The original papers and Maeshowe program have been recovered. The work contains historical comparisons, testable proposals and a working numerical model. The numerical model does **not reproduce the Maeshowe report's headline results**, and its alphabet needs correction or explicit justification before it can be used for historical decipherment. The People manuscript's recurring-pattern argument remains a hypothesis; several particular source-to-claim links need correction.

This review covers the complete recovered People manuscript, both text-identical Maeshowe reports, the associated Pattern Recognition Archaeology report, the companion ledger's ten reported tests, both recovered versions of the Maeshowe code, and relevant locally collected Isambard receipts. Selected external sources were checked directly. It is not a claim that every cited ancient text, image, genetic study or historical experiment has now been independently validated.

## Originals and chronology

| Material | Earliest occurrence in the recovered Git history | Finding |
|---|---|---|
| Maeshowe numerical decoder | 9 March 2026; commit `3c4fa3021113311cc470b630baf0018d6770b112` | Original source recovered; 24-rune mapping and hand-assigned wall/rune frequencies. |
| Maeshowe Seer Decode Report 2026 | 24 March 2026; `7787e45c832ccb216c55dc965df51a16db45a895` | March-dated report; original DOCX SHA-256 `850caff6cd614079274fb9a8b41e863fe874f64691cd2583e6018ee4bd705684`. |
| Maeshowe Seer Decode Report / rev2 | 5 April 2026; `e7b3a462bd991f2c03bbcea256f9c2d2fb9ccdcf` | Different DOCX bytes, but identical extracted text. These are not two independent confirmations or substantive text revisions. |
| Later decoder version | 19 April 2026; `4ea3e68a23b9a43e3f2ec7976954cefc236c487b` | Only a Seer import path differs. Both versions give the same numerical baseline. |
| Pattern Recognition Archaeology | Manuscript dated 30 April 2026; recovered in the May corpus | Connects Maeshowe, an Antarctic candidate and Ogham/Futhork geometry; states several limits and prospective tests. |
| People of the Threshold v1 | Manuscript dated 2 May 2026; first recovered Git occurrence 22 May, `cdb8af76f35760b4008bff568342a19d7f3c6b53` | Full manuscript recovered: seven identity entries, four exchange entries, six knowledge entries and six influence entries. |

Git dates establish recorded repository provenance, not authenticated first authorship or publication dates. The source index records document hashes and all recovered paths.

[People original](C:/Users/samle/Documents/Codex/2026-09-05/k/work/research-history/f85954729805568b84e2050d05b07d1d581fa2a3.docx) · [Maeshowe original](C:/Users/samle/Documents/Codex/2026-09-05/k/work/research-history/dd2cfa85c8e64d220b96c46df23b6d5fef4dd5c2.docx) · [Pattern Recognition original](C:/Users/samle/Documents/Codex/2026-09-05/k/work/research-history/76753aedea8fff1cf1a3b3756c2b0392c1e3735a.docx) · [Full source index](C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/git-research-source-index.json)

Public author records also exist on [ResearchGate](https://www.researchgate.net/publication/404666951_People_of_the_Threshold) and [Academia](https://www.academia.edu/166176974/The_People_of_the_Threshold_Who_They_Were_What_They_Wanted_What_They_Gave_Back_How_the_Knowledge_Shaped_the_World). Their existence does not establish peer review. The July [Substack methodology essay](https://garyleckey.substack.com/p/how-do-you-test-a-pattern-that-crosses) explicitly treats the historical synthesis as a research programme and calls for source-level, falsifiable tests.

## People of the Threshold: what the argument does and does not establish

The manuscript groups stories and records of boundary residents, travellers, offerings and specialist knowledge. It proposes four kinds of exchange and six categories of returned knowledge. This provides a framework for comparative research. Establishing a shared historical population, institution or transmission chain requires additional evidence connecting the specific places, dates and people.

There are three immediate source corrections:

1. **Direction of the Hyperborean exchange.** Sections 2.1–2.2 add a reverse flow towards Hyperborea and describe another party going there. Herodotus 4.33–35 describes offerings and emissaries coming from Hyperborea to Delos. That passage does not establish the asserted reverse route or a 19-year return shipment. Preserve the attested direction; require a separate passage for the added direction. [Herodotus, primary text](https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0126%3Abook%3D4&force=y)
2. **Egyptian identity.** The manuscript acknowledges that the dead king becomes an akh, but subsequently uses the category as support for a population of mortal residents with specialist knowledge. Janák's Egyptological account describes akhu in the relevant funerary setting as transformed dead and intermediaries. The inference from this religious category to an earthly population is unestablished. Retain the boundary/intermediary comparison while correcting the demographic claim. [Janák, *Akh*, pp. 1–3](https://escholarship.org/content/qt7255p86v/qt7255p86v_noSplash_9076a9426b444668ed50eb63ddfc4047.pdf)
3. **Who was present in 1021.** The manuscript attaches that date to Leif Eriksson's journey. Kuitems and colleagues establish Norse presence in Newfoundland in AD 1021; the dating does not identify an individual visitor. The defensible claim is the presence of Norse people, with the saga's named individuals recorded separately. [Authors' university research record](https://research.rug.nl/en/publications/evidence-for-european-presence-in-the-americas-in-ad-1021/)

Other central issues remain open: a shared motif is not itself proof of common ancestry; a source written centuries after an alleged encounter must retain both dates; Greek and Roman accounts that reuse earlier authors cannot count as independent confirmations; and the Hopi, Polynesian, Vedic and Egyptian categories need their own linguistic and cultural context. Geographic and genetic connections must be tied to particular sampled people or objects, rather than transferred to a proposed teaching tradition.

The full 23-entry inventory is retained in the [accompanying claim ledger](C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/threshold-claims-review-20260912.json). Each entry distinguishes the manuscript's assertion from what has actually been checked. The whole seven-tradition synthesis has **not** passed an independent historical test in this review.

## Maeshowe: the numerical reproduction

I ran both recovered, unchanged code versions locally and enumerated all 24 possible pivot inputs accepted by the original model. These are counterfactual inputs, not readings taken from stone or photographs.

| Quantity | March report | Recovered program |
|---|---:|---:|
| Complete inscriptions | 8 of 13 implied by five incomplete | 9 of 13 |
| Mean caller frequency | 369.69 Hz | 369.6923 Hz |
| Mean seer frequency | 397.42 Hz | 398.9756 Hz |
| Master beat | 27.73 Hz | 29.2832 Hz |
| Distance from the 27.3-Hz target | 0.43 Hz | 1.9832 Hz |
| Coherence Γ | 0.8223 | **0.493163** |
| Claimed completion threshold | 0.945 | No pivot candidate reaches it |

The report's Tiwaz/Hagalaz examples are not identical to the program's aggregate inscription selection: the program represents the alphabet with Hagalaz alone and assigns Tiwaz to a different wall. Thus the report's individual examples cannot be substituted for the aggregate output.

Across all 24 hypothetical pivots, Γ ranges from **0.325769 to 0.559061**. A stronger check is possible without choosing a rune. The program uses:

`Γ = 0.50 × phi_score + 0.30 × completeness + 0.20 × Schumann_score`.

Adding only the pivot gives 10/13 completeness. Even making both other scores perfect gives an upper bound of **0.930769**, below 0.945. Under this formula, the pivot alone cannot complete the system. The report does allow other inscriptions as a subsequent step, but any expectation of pivot-only completion is incompatible with the current arithmetic.

The golden-ratio examples also have an identifiable origin. The program multiplies a base frequency by φ or 1/φ, then compares it with that same base. For example, `f/(f×φ)=1/φ`. Reproducing that ratio verifies the chosen transformation; it does not independently detect φ in the carving. The program explicitly selects the alphabet's representative rune for its high phi resonance. That selection must be included in any null test.

No microphone recording, measured chamber impulse response or electromagnetic time series enters these calculations. The 37.53-Hz chamber value is an idealised calculation using 343/(2×4.57), while the 27.3-Hz comparison is a stored target. Neither is an observation of a coupled chamber–Schumann phenomenon.

[Numerical audit and all 24 candidates](C:/Users/samle/Documents/Codex/2026-09-05/k/outputs/maeshowe-original-code-audit-20260912.json)

## Twig runes: the physical reading must come first

The recovered program uses Elder Futhark: three groups of eight, with the first group mapped to Freyr. Barnes describes the Viking/medieval cipher as a 16-character system normally divided 6:5:5, with group numbering commonly reversed. This materially changes the decoding. His paper also discusses a separate Loch of Stenness stone with two apparent twig signs and uncertain interpretation; it has not been established that this is the user's intended pair. [Barnes, *Runic Tradition in Orkney*, printed pp. 5 and 10](https://www.arild-hauge.com/PDF/Barnes_Orkney_2003_pp_4-17.pdf)

For now, “two twig runes” remains an unresolved identification: it could refer to two particular symbols or to the left/right channels used by the Maeshowe model. No separate recovered filename identifies a work with that exact title. Inscription 15, the model's references to 9 and 20, and the Stenness stone must not be silently combined.

The independent 2018 RTI study confirms that inscription 15 was captured and deposited but excluded from that paper's analysis because its scale was unsuitable. That is evidence of a recorded image set, not a published twig count or decipherment. Its north-east diagram places 11, 12, 15 and XXXII there; it is not a complete distribution survey of every inscription. Archive retrieval was unsuccessful in this session, so no physical strokes were counted. [Smith et al., data paper and archive reference](https://intarch.ac.uk/journal/issue47/8/index.html)

Two input counts can be read by one person. The existence of a two-coordinate cipher alone does not establish a requirement for two simultaneous speakers or observers. Such a performance claim needs additional textual or acoustic evidence.

## Associated geometry and reported experiments

One numerical result **does reproduce**: the Pattern Recognition report's stated coordinates, Maeshowe (58.99, −3.19) and Antarctic candidate (−89.19, 110.65), give a spherical initial bearing of **178.5483°** and distance **16,602.46 km**. These match its rounded 178.55° and 16,602 km. This verifies the geographic calculation, not ancient knowledge of the destination.

The inscription population changes across the documents. The code distributes its 13 selected entries as SW 2, NE 5, SE 3, NW 3. The Pattern Recognition report later reasons from SW 2, NE 4, SE 1, NW 1 and calls the last two walls uniquely sparse. Its earlier enumeration is itself inconsistent about eight versus nine selected entries. A selected subset cannot establish the rarity of a wall in the full archaeological corpus. The companion ledger also gives 221° for an alignment where the Pattern Recognition report gives 232°; passage direction and observed horizon sunset direction need separate definitions and sources before any comparison.

The companion Validation Metrics Ledger reports ten tests. Their reported outcomes are preserved below; raw historical run receipts for these ten tests were not located in the inspected local collections and they were not rerun here.

| Reported test | Outcome recorded in the author's ledger | Meaning for this review |
|---|---|---|
| Terrestrial node-distance phi ratios | 28/300; null 25.3 ± 10.6; p=0.40 | No reported excess. |
| Sky-pointer pair ratios | 4; null 10.35 ± 3.08 | Fewer reported matches than random. |
| Selected Pleiades–Belt–Sirius triangle | Ratio 1.629; reported p=0.019 | Candidate result; selection and multiplicity still require audit. |
| Venus/Earth orbital relationship | Ratio 1.6255; near five conjunctions in eight years | Astronomical comparator; does not identify a historical transmission network. |
| Twelve monument alignment windows | Rates 9.89–10.41%; null 10.17 ± 0.15% | No reported excess. |
| Calendar dawn-rising star ratios | 78/378; null 120 ± 16 | Aggregate result is below the null. |
| Particular Pythagorean intervals | Six close matches | Individual matches coexist with the aggregate negative result. |
| Brendan feature-to-geography mapping | Reported as supported through Johnston | Interpretation needs the precise publication and passages checked. |
| Brendan four-station/seven-year structure | Reported as text-internal | A narrative structure, not independent geographic proof. |
| Druid system predates Rome/Christianity | Supported in ledger by Newgrange's date | An old monument's date does not by itself identify its builders as druids. |

The ledger's introduction says five tests failed or failed inversely. Its ten-row table explicitly labels four that way, with another row retaining particular hits alongside an aggregate null. Preserve the actual row-level results rather than an unexplained pass/fail total.

The inspected Isambard records establish that the Maeshowe module compiled and imported (`6174295` sweep), and that a separate sacred-lattice software check passed in `6144042` and `6145730`. Those checks concern execution, determinism, output structure and consent handling. They do not test inscription 15 or authenticate the historical interpretation. The staged research registry explicitly marked these archaeological claims as needing operationalisation and execution.

## Next work, in order

1. Identify the exact two symbols or work intended, and reconcile Barnes/Farrer numbering with a complete inscription register. Keep mark coordinates, wall position, image ID and provenance together.
2. Acquire inscription 15's archived images through an available authorised route. Preserve file hashes, lighting settings and the original resolution. Have independent readers record uncertain strokes before seeing proposed words, frequencies or target Γ values. Ambiguous imaging should be labelled inconclusive; absence of a cipher needs adequately resolving images.
3. Preserve the original program as a historical version. Build a separate, explicitly sourced medieval decoder with documented order/orientation variants and checks against known inscriptions. Keep uncertain marks as alternatives; never choose the reading that gives the preferred coherence.
4. Reconcile the paper's baseline and completeness counts. Treat frequencies, semantic rune assignments and Γ thresholds as model choices unless measured evidence supports them. Test any revised statistic against controls that include all selections and tunable mappings.
5. Recover the original geometry scripts cited only as `/home/claude/celtic/`; their named figure/script stems were not found in the recovered Git path inventory. Then run the report's south-polar specificity and all-bearing controls. Do not call a newly reconstructed calculation an exact rerun.
6. Correct the three specific People source problems above, then verify each of its 23 entries against exact passages and dated evidence. Distinguish source chronology, reported event chronology, material links and proposed transmission links. Retain failed tests alongside candidate findings.

Large GPU runs are not the next dependency for this strand. The immediate work is inscription identification, source recovery, decoder correctness and a statistically defined comparison. The original manuscripts and repository source have been preserved unchanged; this review and numerical audit are separate artifacts.
