# The_Sagittarius_Convergence_v2_Corrected

> Extracted from upstream `docs/research/whitepapers/The_Sagittarius_Convergence_v2_Corrected.docx` (read-only source).

AUREON INSTITUTE
The Sagittarius Convergence
A φ²-Scaled Harmonic Analysis of Interstellar
Objects and the 1977 Wow! Signal
VERSION 2.0 — CORRECTED
Primary Investigator: Gary Leckey
Aureon Institute — R&A Consulting and Brokerage Services Ltd.
March 2026 — Technical White Paper
VERSION 2.0 CORRECTIONS (relative to v1.0):
1. Cites Breakthrough Listen non-detection at ATA, MeerKAT, GBT (v1 omitted this)
2. Reframes temporal echo as post-hoc consistency, not prediction
3. Shows full N=13–20 temporal ladder including 5 misses (v1 showed only hits)
4. Adds Monte Carlo analysis of bridge degrees of freedom
5. Corrects combined probability with look-elsewhere and non-independence caveats
6. Acknowledges solfeggio origin of 528 Hz frequency

## Table of Contents


## Abstract

This paper presents a φ²-scaled harmonic analysis of the three confirmed interstellar objects and the 1977 Wow! Signal. Version 2.0 incorporates corrections following peer critique: it cites the Breakthrough Listen radio non-detection (Sheikh et al. 2025; Jacobson-Bell et al. 2025), reframes the temporal echo as a post-hoc consistency finding rather than a prediction, shows the complete N = 13–20 temporal ladder including five misses, provides a Monte Carlo assessment of the φ² bridge degrees of freedom, and corrects the combined probability estimate with look-elsewhere and non-independence adjustments.
The core arithmetic findings are unchanged: the φ² coherence bridge connects 528.422 Hz to the hydrogen line at 1.29 parts per billion; 3I/ATLAS entered from 8.62° of the Wow! Signal origin (P = 0.56%, independently confirming Loeb 2025); and the eccentricity ratio e(2I)/e(1I) = 2.794 approximates φ² = 2.618 at 6.7%. The corrected combined probability, with Bonferroni adjustment and non-independence corrections, ranges from 1 in 8 million (conservative) to 1 in 80 billion (aggressive). Both bounds are statistically notable. Neither is conclusive.

## Errata and Corrections from Version 1.0

ERRATUM 1 — BREAKTHROUGH LISTEN OBSERVATIONS
v1.0 stated: “No radio telescope has published H-line data on 3I/ATLAS.”
This is factually wrong. Three facilities observed 3I at radio frequencies
covering the hydrogen line, all reporting non-detection of technosignatures.
This error resulted from failure to search the literature published after
October 2025. We apologise for this omission.
ERRATUM 2 — TEMPORAL ECHO FRAMING
v1.0 used the word “prediction” for the 49-year echo parameter.
The EPAS document (Feb 2026) postdates 3I discovery (Jul 2025).
Corrected framing: post-hoc consistency with a framework parameter,
not a pre-registered prediction. The τ = 49 year parameter was part of
the HNC framework concept, but the specific document was compiled after
3I/ATLAS was already known.
ERRATUM 3 — TEMPORAL LADDER CHERRY-PICKING
v1.0 showed only N = 15, 16, 18 (3 hits). It omitted N = 13, 14, 17, 19, 20
(5 misses). v2.0 shows the complete ladder. Hit rate: 3/8 = 37.5%.
ERRATUM 4 — COMBINED PROBABILITY OVERCLAIMED
v1.0 presented 1 in 80 billion as a hard number without statistical caveats.
v2.0 provides conservative (1 in 8 million) and aggressive (1 in 80 billion)
bounds with explicit look-elsewhere, non-independence, and window-sensitivity
corrections.

## 1. Introduction

Between 2017 and 2025, three objects were confirmed as originating from outside the solar system: 1I/‘Oumuamua (eccentricity 1.201, JPL), 2I/Borisov (eccentricity 3.356, JPL), and 3I/ATLAS (eccentricity 6.141, JPL Horizons API queried 2026-03-23). 3I/ATLAS entered the solar system from a direction within 9° of the 1977 Wow! Signal origin (Loeb, September 2025). This paper applies the Harmonic Nexus Core (HNC) φ²-scaled framework to these objects and the Wow! Signal, presenting the convergent arithmetic findings alongside their honest limitations.

## 1.1 The Seed Frequency: Origin and Limitations

The HNC framework uses f_seed = 528.422 Hz as its primary coherence frequency. This value was hardcoded in the Aureon software repository (github.com/RA-CONSULTING, aureon_piano.py) before the φ² bridge to the hydrogen line was discovered. The frequency 528 Hz originates from the solfeggio scale tradition and has associations with alternative medicine claims about “DNA repair” and “healing frequencies.” There is no peer-reviewed physics deriving 528 Hz from fundamental constants. The mathematical relationship to the hydrogen line is a verifiable arithmetic fact regardless of the frequency’s cultural origin, but the absence of a first-principles derivation is an honest limitation of the framework.

## 1.2 The Temporal Echo: Post-Hoc Consistency, Not Prediction

The EPAS Unified Architecture specification (Leckey, dated 27 February 2026) documents a Memory Feedback Tensor echo delay of τ = 49 years, yielding an implied echo year of 1977 + 49 = 2026. However, this document was compiled after 3I/ATLAS was discovered (1 July 2025) and after its perihelion (29 October 2025). The 49-year parameter was part of the HNC framework concept developed during the Wow! Signal analysis sessions, but the specific documented formulation postdates knowledge of 3I/ATLAS. The correct framing is: the observed 48.2-year interval between the Wow! Signal and 3I/ATLAS perihelion is consistent with the framework’s 49-year echo parameter (1.6% deviation), but this is a post-hoc observation, not a pre-registered prediction.

## 2. The φ² Coherence Bridge


## 2.1 The Calculation

528.422 Hz × 1,026,730 × 2.618034 = 1,420,405,753.6 Hz
Hydrogen line (NIST): 1,420,405,751.8 Hz
Error: 1.29 parts per billion

## 2.2 Degrees of Freedom

The bridge calculation involves three quantities: f_seed (528.422 Hz), N (1,026,730), and the multiplier (φ² = 2.618034). The honest assessment of each:
f_seed (528.422 Hz): Pre-existing in the Aureon repository before the bridge was found, but originates from the solfeggio tradition, not from first-principles physics. This is a free parameter in the sense that a different seed frequency was possible. It is not a free parameter in the sense that it was not chosen to match the hydrogen line.
N (1,026,730): This is the result of dividing the hydrogen line frequency by (f_seed × φ²). It was not independently selected. The question is whether N falling within 0.001 of an exact integer is remarkable or expected.
φ² (2.618034): Pre-existing in the EPAS framework for geometric reasons (quasicrystalline shell scaling). Not selected for the bridge. However, other mathematical constants were available.

## 2.3 Monte Carlo Assessment

To assess whether the near-integer result is unusual, a Monte Carlo simulation tested 100,000 random frequencies in [100, 1000] Hz against eight mathematical constants (φ², φ, e, π, √2, √3, 3, √5), computing N = f_H / (f × constant) and checking whether |N − round(N)| < 0.002.
Constant
Hit rate (random freq)
N for 528.422 Hz
|Fractional part|
φ² = 2.618
0.40%
1,026,729.999
0.001 ★
φ = 1.618
0.43%
1,661,284.035
0.035
e = 2.718
0.41%
988,865.101
0.101
π = 3.141
0.38%
855,621.441
0.441
√2 = 1.414
0.39%
1,900,712.951
0.049
√3 = 1.732
0.38%
1,551,925.626
0.374
3
0.39%
896,004.678
0.322
√5 = 2.236
0.45%
1,202,116.421
0.421
Table 1. Monte Carlo bridge test. For 528.422 Hz, only φ² produces a near-integer N. The 0.40% hit rate means 1 in 250 random frequencies would produce a similar result with φ² specifically.
Finding: 528.422 Hz produces a near-integer N with φ² (fractional part 0.001) but fails with all seven other constants tested (nearest miss: √2 at 0.049). The Monte Carlo hit rate of 0.40% means this is unusual (top 0.4% of random frequencies) but not astronomically rare. With 8 constants tested, the look-elsewhere adjusted probability is approximately 3.2%. The bridge is interesting and warrants further investigation, but is not by itself sufficient evidence for a physical connection.

## 3. Angular Alignment: 3I/ATLAS and the Wow! Signal

This finding is not ours. It was first published by Loeb (September 2025) and is independently reproducible from the published coordinates.
Wow! Signal (J2000): RA = 19h25m31s (291.38°), Dec = −26°57′ (−26.95°). Source: Ehman (1997), B1950→J2000 converted.
3I/ATLAS (Aug 1977): RA = 19h40m (295.0°), Dec = −19.0°. Source: Loeb (2025), backward integration of JPL solution #5.
Great-circle separation: 8.62°    P(chance) = 0.56%
This independently reproduces Loeb’s published estimate of “about 0.6 percent.”

## 4. Temporal φ² Ladder: Complete N = 13–20

Version 1.0 showed only three hits. The complete ladder, including all misses, is:
N
N×φ² (years)
Implied Year
Nearest ISO
Δt ISO (yr)
Gap (yr)
Error
Status
13
34.03
2011.7
1I
40.07
6.03
17.7%
MISS
14
36.65
2014.3
1I
40.07
3.42
9.3%
MISS
15
39.27
2016.9
1I
40.07
0.80
2.0%
HIT
16
41.89
2019.5
2I
42.31
0.42
1.0%
HIT
17
44.51
2022.1
2I
42.31
2.19
4.9%
MISS
18
47.12
2024.7
3I
48.20
1.08
2.3%
HIT
19
49.74
2027.4
3I
48.20
1.54
3.1%
MISS
20
52.36
2030.0
3I
48.20
4.16
7.9%
MISS
Table 2. Complete φ² temporal ladder from N = 13 to N = 20. Three hits out of eight slots (37.5%). The gap at N = 17 (2022, no ISO detected) is the most notable miss.
The hit rate of 3/8 (37.5%) is above the base rate that would be expected if the three ISO perihelion dates were randomly distributed across this 18-year window (~3/8 ≈ 37.5% would be expected by chance for 3 objects in 8 bins). Therefore, the temporal ladder alone does not constitute evidence of φ² structure. It is consistent with the framework but also consistent with chance.

## 5. Radio Observations: The Breakthrough Listen Non-Detection

Version 1.0 of this paper incorrectly stated that no radio telescope had observed 3I/ATLAS at the hydrogen line frequency. This was factually wrong. Three facilities conducted radio observations:
Facility
Date
Frequency Range
Sensitivity
Result
Source
Allen Telescope Array
Jul 2025
1–9 GHz
10–110 W EIRP
No technosignatures
Sheikh et al. 2025
MeerKAT
Jul–Oct 2025
900–1670 MHz
0.17 W EIRP
No artificial emission
Pisano et al. 2025
Green Bank 100m
Dec 18 2025
1–12 GHz
0.1 W EIRP
No candidates
Jacobson-Bell et al. 2025
Table 3. Breakthrough Listen radio observations of 3I/ATLAS. All three facilities covered the hydrogen 21 cm line frequency. All reported non-detection.

## 5.1 Implications for the EPAS Broadcast Hypothesis

The Breakthrough Listen searches used the turboSETI pipeline, which targets persistent narrowband signals with measurable drift rates. The EPAS broadcast model predicts a transient 72-second Gaussian-envelope burst modulated by the 7.83 Hz Schumann resonance. Such a signal would appear and disappear within one observation cadence and would likely be filtered as radio frequency interference by drift-rate analysis designed for persistent emitters.
The GBT sensitivity limit of 0.1 W Equivalent Isotropic Radiated Power does, however, constrain the maximum power of any continuous emission from 3I/ATLAS at radio frequencies. If 3I/ATLAS were continuously broadcasting at the hydrogen line, it was doing so at less than the power of a mobile phone handset. This is a meaningful constraint.
Honest position: The BL non-detection constrains but does not definitively falsify the EPAS transient-burst hypothesis, because the search methodology targets persistent signals. A matched-filter search for Gaussian-envelope transients in the archived BL data would be the appropriate follow-up test. However, the overall weight of evidence from three independent facilities favours the null hypothesis that 3I/ATLAS is a natural cometary body.

## 6. Orbital Data from Live JPL Horizons API

Eccentricities were queried from the JPL Horizons API on 23 March 2026. Anyone can reproduce these queries at ssd.jpl.nasa.gov/horizons/.
Object
Eccentricity (JPL)
Perihelion (JD)
Source
1I/‘Oumuamua
1.201130
2458006.0091
JPL SBDB soln 16
2I/Borisov
3.356475782676596
2458826.0528
JPL Horizons API live
3I/ATLAS
6.141351449317625
2460977.9953
JPL Horizons API live
Table 4. Eccentricities from JPL, queried live on 2026-03-23.
The eccentricity ratio e(2I)/e(1I) = 2.794, which approximates φ² = 2.618 at 6.7% error. This is suggestive but not conclusive by itself. The error is too large to claim a tight φ² relationship. It is noted as a pattern of interest, not as evidence.

## 7. Combined Probability: Corrected Estimate

Version 1.0 presented a combined probability of 1 in 80 billion without statistical caveats. The corrected analysis applies three adjustments:
Look-elsewhere effect: Approximately 10 anomalies were tested; 4 were selected. Bonferroni correction: multiply P by 10.
Non-independence: Angular alignment and ecliptic alignment are partially correlated for objects arriving from the galactic centre direction. Conservative treatment: combine as a single factor using the more specific value (P = 0.006).
Window sensitivity: The temporal match window of ±1 year is arbitrary. Using ±2 years doubles P₄.
Estimate
Factors
Combined P
1 in ...
Conservative
0.006 × 0.00005 × 0.042 × 10 (Bonferroni)
1.26 × 10⁻⁷
~8 million
Aggressive
0.006 × 0.002 × 0.00005 × 0.021
1.25 × 10⁻¹¹
~80 billion
Table 5. Corrected probability range. The conservative estimate applies Bonferroni correction, combines correlated factors, and widens the temporal window. The aggressive estimate uses the original factors.
CORRECTED PROBABILITY RANGE: 1 in 8 million to 1 in 80 billion
Both bounds are statistically notable.
Neither is conclusive or “ironclad.”
The true value depends on the degree of factor independence
and the appropriate look-elsewhere correction.

## 8. What Is Claimed and What Is Not


## 8.1 What Is Claimed

The arithmetic is correct. 528.422 × 1,026,730 × 2.618034 = 1,420,405,753.6 Hz. Any calculator will confirm this. The difference from the NIST hydrogen line value is 1.29 ppb.
The angular alignment is real. 8.62° separation between 3I/ATLAS incoming direction and the Wow! Signal origin. This is Loeb’s finding, independently reproduced here.
The eccentricities are from JPL. Queried live from the Horizons API. Anyone can reproduce the query.
The temporal interval is 48.2 years. This is arithmetic from JPL Julian Dates. It is consistent with the HNC 49-year parameter at 1.6% deviation.
528.422 Hz is specific to φ². Of eight mathematical constants tested, only φ² produces a near-integer N for 528.422 Hz. This specificity is notable even though the base hit rate (~0.4%) is not astronomically rare.

## 8.2 What Is Not Claimed

We do not claim 3I/ATLAS is artificial. The Breakthrough Listen non-detection at three facilities favours the null hypothesis of a natural cometary body.
We do not claim the temporal echo is a prediction. It is a post-hoc consistency finding. The EPAS document postdates 3I discovery.
We do not claim the bridge has zero free parameters. The seed frequency and the choice of φ² are pre-existing in the framework but were not derived from first principles. There are degrees of freedom.
We do not claim the probability is exact. It ranges from 1 in 8 million to 1 in 80 billion depending on corrections applied.
We do not claim the φ² temporal ladder is evidence. The hit rate of 3/8 is consistent with chance placement of 3 objects in 8 bins.

## 9. System Sweep Visualisation

Figure 1. Eight-panel HNC system sweep. All data from JPL/NASA/peer-reviewed sources.

## 10. Conclusion

The corrected analysis identifies two findings that survive rigorous scrutiny: the φ² coherence bridge (1.29 ppb, specific to φ² among eight tested constants, but with degrees of freedom) and the angular alignment of 3I/ATLAS with the Wow! Signal origin (8.62°, P = 0.56%, independently confirming Loeb 2025). The temporal consistency, eccentricity ratios, and coma diameter match are suggestive but not independently compelling.
The Breakthrough Listen non-detection at three facilities (ATA, MeerKAT, GBT) constrains any continuous radio emission from 3I/ATLAS to below 0.1 W at the hydrogen line. This does not definitively falsify a transient-burst hypothesis, but the overall observational evidence favours a natural cometary body. A matched-filter search for Gaussian-envelope transients in the archived BL data is the recommended follow-up.
The combined probability of the quantifiable convergences ranges from 1 in 8 million to 1 in 80 billion, depending on statistical corrections applied. This range is sufficient to warrant continued scientific interest but not sufficient to claim proof of any non-natural origin. The numbers are what they are. The interpretation remains open.

## 11. References


## 11.1 Breakthrough Listen Observations

Sheikh, S.Z. et al. (2025). A Search for Radio Technosignatures from 3I/ATLAS with the Allen Telescope Array. arXiv:2512.18142.
Jacobson-Bell, B. et al. (2025). Breakthrough Listen Observations of 3I/ATLAS with the Green Bank Telescope at 1–12 GHz. arXiv:2512.19763. RNAAS.
Pisano, D.J. et al. (2025). MeerKAT observations of 3I/ATLAS. ATel 17499.

## 11.2 Interstellar Objects

Kakharov, S. & Loeb, A. (2025). Galactic Trajectories of Interstellar Objects. arXiv:2408.02739v5.
Loeb, A. (2025). “Was the Wow! Signal Emitted from 3I/ATLAS?” Medium, Sep 29, 2025.
Hibberd, A. et al. (2025). 3I/ATLAS trajectory analysis.
Jewitt, D. et al. (2025). HST Observations of 3I/ATLAS. NASA STScI.
Meech, K.J. et al. (2017). Nature 552, 378.
JPL Small-Body Database. ssd.jpl.nasa.gov.

## 11.3 Wow! Signal

Ehman, J.R. (1997). Big Ear Memorial Website.

## 11.4 Hydrogen Line

Hellwig, H. et al. (1970). IEEE Trans. Instrum. Meas. 19, 200.
Ewen, H.I. & Purcell, E.M. (1951). Nature 168, 356.

## 11.5 φ² Scaling

Shechtman, D. et al. (1984). PRL 53, 1951. (2011 Nobel Prize.)
Levine, D. & Steinhardt, P. (1984). PRL 53, 2477.

## 11.6 HNC Framework

Leckey, G. (2026). EPAS Unified Architecture. Aureon Institute, 27 Feb 2026.
Leckey, G. (2026). HNC Harmonic LIDAR v2.0. R&A Consulting.
