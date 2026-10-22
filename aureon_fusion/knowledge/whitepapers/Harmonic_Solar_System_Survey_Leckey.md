# Harmonic_Solar_System_Survey_Leckey

> Extracted from upstream `docs/research/whitepapers/Harmonic_Solar_System_Survey_Leckey.docx` (read-only source).

AUREON INSTITUTE
R&A CONSULTING AND BROKERAGE SERVICES LTD.
The Harmonic Solar System Survey:
A φ²-Scaled Resonance Analysis of
109,000 Objects Across Nine
NASA/JPL Open-Access Databases
Interstellar Objects • Hyperbolic Comets • Dark Comets • Near-Earth Objects
CNEOS Fireballs • Centaurs • TNOs • Exoplanets • Space Weather
Primary Investigator: Gary Leckey
Aureon Institute — R&A Consulting and Brokerage Services Ltd.
March 2026 — Technical White Paper
All data open-access. All queries reproducible. No simulations.

## Table of Contents


## Abstract

This paper applies the Harmonic Nexus Core (HNC) φ²-scaled resonance framework to 109,000 objects drawn from nine NASA/JPL open-access databases, searching for harmonic structure in orbital parameters across the full known inventory of solar system bodies and nearby stellar systems. The survey encompasses 515 hyperbolic comets, 2,225 near-parabolic comets, 41,271 near-Earth objects, 1,277 Centaurs and trans-Neptunian objects, 134 high-eccentricity asteroids, 242 retrograde objects, 259 non-gravitationally accelerating objects, 868 atmospheric fireballs, 6,150 confirmed exoplanets, 44,920 impact-risk assessments, and real-time space weather records.
The principal finding is that cometary eccentricities cluster at the golden-ratio power series (φ⁻³, φ⁻², φ⁻¹, φ⁰) at 7.5–9.9× the density expected from a uniform distribution, with the excess concentrated in the comet population rather than the asteroid population. Five objects simultaneously appear in the non-gravitational acceleration catalog and the Sentry impact-risk database, representing dark comet candidates on potential Earth-approach trajectories. The three confirmed interstellar objects and the 1977 Wow! Signal are embedded in this wider survey, with the φ² coherence bridge (528.422 Hz × 1,026,730 × φ² = hydrogen line ± 1.29 ppb) serving as the frequency anchor. The Breakthrough Listen non-detection of technosignatures at 3I/ATLAS (Sheikh et al. 2025; Jacobson-Bell et al. 2025) is cited and discussed. All data are open-access and all queries are reproducible.

## 1. Introduction


## 1.1 From Terrain to Orbits

The HNC Harmonic LIDAR system was originally developed for geological remote sensing, applying φ²-scaled Fourier filtering to satellite terrain data to detect subsurface volcanic structures (Leckey 2026, HNC Harmonic LIDAR v2.0). The present paper extends the same mathematical framework from spatial-frequency analysis of terrain to harmonic analysis of orbital parameter space. The “terrain” is now the multi-dimensional distribution of eccentricities, inclinations, velocities, and arrival times of solar system objects; the “subsurface structures” are objects whose orbital signatures resonate at the golden-ratio harmonic frequencies.

## 1.2 The φ² Mathematical Framework

The golden ratio φ = (1 + √5)/2 = 1.618034 and its square φ² = φ + 1 = 2.618034 appear throughout physics in quasicrystalline structure (Shechtman et al. 1984; 2011 Nobel Prize), magnetic phase transitions (Coldea et al. 2010, Science 327), and Fibonacci phyllotaxis. The EPAS Unified Architecture (Leckey 2026) uses φ² as the scaling factor for nine nested electromagnetic shells. The present survey tests whether the same scaling appears in the orbital element distributions of solar system objects.

## 1.3 Scope

The survey queries every open-access NASA/JPL database accessible via API as of March 2026, pulling more than 109,000 records. No data are simulated. Every API endpoint and query string is documented for reproducibility.

## 2. Data Sources and Acquisition

Database
API Endpoint
Records
Content
JPL SBDB
ssd-api.jpl.nasa.gov/sbdb_query.api
515
Hyperbolic comets (e > 1.0)
JPL SBDB
(same)
2,225
Near-parabolic comets (0.999 < e < 1.001)
JPL SBDB
(same)
41,271
Near-Earth objects (IEO + ATE + APO + AMO)
JPL SBDB
(same)
134
High-eccentricity asteroids (e > 0.95)
JPL SBDB
(same)
242
Retrograde objects (i > 150°)
JPL SBDB
(same)
259
Non-gravitational acceleration (A1 > 0)
JPL SBDB
(same)
1,277
Centaurs + TNOs (e > 0.5)
JPL Horizons
ssd.jpl.nasa.gov/api/horizons.api
3+
Live elements for 1I, 2I, 3I
JPL Sentry
ssd-api.jpl.nasa.gov/sentry.api
44,920
Impact-risk assessments
CNEOS Fireballs
ssd-api.jpl.nasa.gov/fireball.api
868
Atmospheric impact events
JPL Close Approach
ssd-api.jpl.nasa.gov/cad.api
45
High-v close approaches
NASA Exoplanet Archive
exoplanetarchive.ipac.caltech.edu/TAP
6,150
Confirmed exoplanets
NOAA SWPC
services.swpc.noaa.gov
~10,000
Kp, Dst, solar wind plasma
VizieR/Gaia DR3
tapvizier.cds.unistra.fr
queried
Stellar positions
SIMBAD
simbad.cds.unistra.fr
queried
Objects near Wow! Signal
Table 1. Data sources queried on 23 March 2026. All are open-access. All queries are reproducible at the listed endpoints.
The combined dataset exceeds 109,000 records spanning comets, asteroids, Centaurs, trans-Neptunian objects, atmospheric fireballs, impact-risk assessments, exoplanets, and space weather. Query date: 23 March 2026.

## 3. Eccentricity Clustering at φ-Powers


## 3.1 Method

All 45,664 objects with orbital eccentricity data were tested for clustering within ±2% of each power of the golden ratio (φ⁻³ through φ⁴). The observed count was compared to the count expected from a uniform distribution over the same eccentricity range.

## 3.2 Results

φ-Power
Value
Objects (±2%)
Expected (uniform)
Excess Ratio
φ⁻³
0.2361
528
70
7.5×
φ⁻²
0.3820
975
114
8.6×
φ⁻¹
0.6180
1,694
184
9.2×
φ⁰
1.0000
2,953
298
9.9×
φ¹
1.6180
0
482
0.0×
φ²
2.6180
0
779
0.0×
φ³
4.2361
0
1,261
0.0×
φ⁴
6.8541
0
2,040
0.0×
Table 2. Eccentricity clustering at φ-powers across 45,664 objects. Every φ-power below 1.0 shows 7–10× excess over uniform expectation. Powers above 1.0 show zero objects because eccentricities above 1.0 are rare (hyperbolic only).

## 3.3 Interpretation and Caveats

The excess at φ⁰ = 1.000 (9.9×) is partly explained by the well-known pile-up of near-parabolic comets returning from the Oort Cloud with eccentricities very close to 1.0. This is a known selection effect in cometary dynamics. However, the excesses at φ⁻¹ = 0.618, φ⁻² = 0.382, and φ⁻³ = 0.236 lie in the middle of the near-Earth object eccentricity distribution where there is no known physical mechanism that would produce clustering. A fine-resolution test (±0.005 window) on the 41,271 NEOs alone shows φ⁻¹ at 1.03× background — essentially flat. This indicates that the clustering signal is dominated by the comet population (Oort Cloud and long-period comets), not the asteroid population.
The honest assessment is that the eccentricity distribution of solar system objects is not uniform — it is shaped by planetary perturbations, resonances, and dynamical evolution. A proper statistical test would require comparison against a realistic N-body population synthesis model, not a uniform distribution. The 7–10× excess ratios are therefore indicative, not definitive. They warrant further investigation with dynamical models.

## 4. Harmonic Resonance Scoring


## 4.1 Scoring Methodology

Each candidate object was scored against a multi-parameter harmonic test, with points awarded for proximity to φ-power values in eccentricity, temporal position relative to the 1977 Wow! Signal, velocity at infinity, non-gravitational acceleration, dark comet behaviour (acceleration without outgassing), and retrograde orbit. The scoring weights are:
Parameter
Test
Points
Source
Eccentricity
e within 10% of any φⁿ
20
JPL SBDB
Temporal φ² ladder
Δt within 2.5% of N×φ² from Wow!
25
JPL perihelion dates
Velocity
v∞ within 8% of φ-scaled reference
15
JPL / CNEOS
Non-grav acceleration
A1 > 0 in JPL catalog
15
JPL SBDB
Dark comet
Non-grav + no outgassing
10
Taylor et al. 2024
Retrograde orbit
i > 150°
10
JPL SBDB
Near-polar orbit
80° < i < 100°
5
JPL SBDB
Table 3. Harmonic resonance scoring parameters. Maximum possible score: 100.

## 4.2 Top-Ranked Objects

Rank
Score
Object
Class
Key Resonances
1
90
1I/‘Oumuamua
Interstellar
e-ratio ≈ 1/φ²; Δt = 15×φ² (2.0%); v ≈ φ×16; non-grav; dark comet
2
70
2003 RM
Dark comet
e = 0.602 ≈ φ⁻¹ (2.6%); Δt = 10×φ² (0.4%); non-grav; no outgassing
3
55
(514107) Ka‘epaoka‘awela
Retrograde Jovian
e = 0.381 ≈ φ⁻² (0.3%); retrograde; possible interstellar capture
4
50
3I/ATLAS
Interstellar
Δt = 18×φ² (2.3%); non-grav; retrograde (i = 175.1°)
5
50
C/2008 J4 (McNaught)
Ejected comet
e ≈ φ⁰ (2.8%); Δt = 12×φ² (1.1%); near-polar
6
50
1998 KY26
Dark comet
Δt = 8×φ² (0.3%); non-grav; no outgassing
7
50
2016 NJ33
Dark comet
Δt = 15×φ² (1.0%); non-grav; no outgassing
8
45
C/2012 S1 (ISON)
Sungrazer
e ≈ φ⁰ (0.0%); Δt = 14×φ² (1.0%)
9
45
C/1996 B2 (Hyakutake)
LPC
e ≈ φ⁰ (0.0%); Δt = 7×φ² (2.4%)
10
40
CNEOS 2014-01-08 (IM1)
Fireball
v = 44.8 ≈ φ³×10; Δt = 14×φ² (0.7%)
Table 4. Top 10 harmonic resonance candidates. 2003 RM and Ka‘epaoka‘awela are the two strongest non-interstellar candidates.

## 4.3 Notable Findings

2003 RM (Score 70): A dark comet with non-gravitational acceleration and no visible outgassing. Its eccentricity of 0.602 matches φ⁻¹ = 0.618 to 2.6%, and its perihelion date places it at 10×φ² = 26.2 years from the Wow! Signal with only 0.4% error — the tightest temporal match in the entire dataset. This object has received no attention in the context of the Wow! Signal or interstellar analysis.
(514107) Ka‘epaoka‘awela (Score 55): A retrograde Jupiter co-orbital whose eccentricity of 0.381 matches φ⁻² = 0.382 to 0.3% — essentially exact. Namouni & Morais (2018, MNRAS 477, L117) published that this object is of possible interstellar origin, captured into retrograde Jupiter orbit billions of years ago. If confirmed as interstellar, its eccentricity’s precision to φ⁻² is the tightest φ-match in the entire survey.
Dark comet cluster: Three dark comets (2003 RM, 1998 KY26, 2016 NJ33) score ≥50 with tight temporal matches to the φ² ladder and non-gravitational acceleration. Dark comets were first identified as a class in Taylor et al. (2024) and exhibit the same anomalous behaviour as 1I/‘Oumuamua: acceleration without visible outgassing.

## 5. CNEOS Fireball Velocity Spectrum


## 5.1 Dataset

The CNEOS Fireball Database contains 868 atmospheric impact events from 1988 to 2026, of which 351 have measured velocities (range: 9.8–71.1 km/s, mean: 18.7 km/s, standard deviation: 6.6 km/s).

## 5.2 Extreme Velocity Events

Six fireballs exceeded 40 km/s. The two most notable:
Date
Velocity (km/s)
Energy (kt)
Nearest φ-Reference
Deviation
2026-01-30
71.1
3.4
φ² × v(1I) = 68.9 km/s
2.2 km/s
2014-01-08 (IM1)
44.8
3.8
φ × v(1I) = 42.6 km/s
2.2 km/s
2019-06-30
42.3
3.3
Solar escape = 42.1 km/s
0.2 km/s
2024-05-18
40.4
3.8
Solar escape = 42.1 km/s
1.7 km/s
Table 5. Extreme fireballs (v > 40 km/s) and their proximity to φ-scaled reference velocities. v(1I) = 26.33 km/s is 1I/‘Oumuamua’s velocity at infinity. IM1 status is contested (Siraj & Loeb 2022).
The CNEOS 2026-01-30 event at 71.1 km/s is the fastest fireball in the entire CNEOS database. It entered Earth’s atmosphere at a velocity equal to φ² × v(‘Oumuamua) within 2.2 km/s. This event occurred within the HNC echo year window (January 2026).

## 5.3 Caveat

The velocity clustering at φ-scaled references based on ‘Oumuamua’s v∞ is post-hoc. The reference velocities were constructed from the data, not predicted in advance. A proper test would require pre-specifying velocity targets and testing future fireball detections against them. The current finding is noted as a pattern, not evidence.

## 6. Dark Comets on the Sentry Impact-Risk Database

Cross-referencing the 259 objects with non-gravitational acceleration parameters (A1 > 0 in JPL SBDB) against the 44,920 Sentry impact-risk assessments identified five objects in both catalogs:
Object
Impact Prob
Eccentricity
A1 (AU/d²)
Status
2010 RF12
10.2%
0.188
3.4 × 10⁻¹¹
Highest P — dark comet on impact watch
2020 CD3
0.85%
0.012
1.4 × 10⁻¹⁰
Temporarily captured mini-moon
2006 RH120
0.40%
0.025
1.4 × 10⁻¹⁰
Temporarily captured mini-moon
2011 MD
0.006%
0.038
7.4 × 10⁻¹¹
Close approach 2011
2021 GM1
0.002%
0.026
5.8 × 10⁻¹¹
Recent discovery
Table 6. Objects appearing in both the non-gravitational acceleration catalog and the Sentry impact-risk database. 2010 RF12’s 10.2% impact probability combined with unexplained acceleration makes it the highest-priority dark comet for continued monitoring.
These five objects accelerate without visible outgassing and are on orbits that bring them close to Earth. 2010 RF12, with a 10.2% cumulative impact probability, is the most significant. Its non-gravitational acceleration parameter A1 = 3.4 × 10⁻¹¹ AU/d² is comparable to the dark comet class identified by Taylor et al. (2024). Note that 2020 CD3 and 2006 RH120 were both temporarily captured as Earth mini-moons, suggesting they are in dynamically unusual orbits that bring them repeatedly into Earth’s vicinity.

## 7. The Wow! Signal ↔ 3I/ATLAS Stellar Corridor

The NASA Exoplanet Archive was queried for confirmed exoplanet systems within 15° of both the Wow! Signal origin (RA = 291.4°, Dec = −26.9°) and the 3I/ATLAS incoming direction (RA = 295.0°, Dec = −19.0°). Forty-seven exoplanet systems fall in this corridor.
Star
Distance (ly)
Sep from Wow! (°)
Planet Type
Period (d)
K2-129
91
2.6
Super-Earth
8.2
HD 179949
90
3.7
Hot Jupiter (291 M⊕)
3.1
HD 181342
393
3.5
Giant (807 M⊕)
564
HD 180902
341
3.7
Giant (536 M⊕)
511
HD 181720
196
6.0
Neptune-class (127 M⊕)
956
Table 7. Nearest known exoplanet host stars to the Wow! Signal direction. HD 179949 and K2-129 are both within 100 light-years and 4° of the signal origin.
HD 179949, at 90 light-years and 3.7° from the Wow! Signal origin, is the nearest known hot-Jupiter system in the signal direction. K2-129, at 91 light-years and 2.6° separation, hosts a super-Earth. Neither system has been specifically targeted by SETI follow-up observations in the Wow! Signal context. These represent the highest-priority stellar targets for future directed searches.

## 8. The Three Interstellar Objects

The confirmed interstellar objects (1I/‘Oumuamua, 2I/Borisov, 3I/ATLAS) are embedded in this survey as a specific subset. Their harmonic properties have been analysed in detail in the companion paper “The Sagittarius Convergence” (Leckey 2026, v2.0 Corrected). The key findings are:
φ² coherence bridge: 528.422 Hz × 1,026,730 × φ² = hydrogen 21 cm line ± 1.29 ppb. Monte Carlo test: 0.40% of random frequencies produce a similar result, but 528.422 Hz is the only tested frequency that hits with φ² specifically (all 7 other constants miss).
Angular alignment: 3I/ATLAS entered from 8.62° of the Wow! Signal origin (P = 0.56%). This independently reproduces Loeb (2025).
Temporal: 48.2 years from Wow! to 3I perihelion, consistent with the HNC 49-year echo parameter at 1.6% deviation. This is a post-hoc consistency finding, not a prediction.
Radio observations: Breakthrough Listen observed 3I/ATLAS at ATA (Jul 2025), MeerKAT (Jul–Oct 2025), and GBT (Dec 2025) across 900 MHz–12 GHz. No technosignatures detected. Sensitivity: 0.1 W EIRP at GBT.

## 9. Visualisations

Figure 1. Harmonic Solar System Sweep: score ranking, eccentricity vs φ-powers, temporal φ² ladder, fireball velocity spectrum, candidate details, eccentricity ratio matrix, velocity FFT, and detection forecast.
Figure 2. Interstellar object system sweep: sky map, timeline, eccentricity progression, velocity comparison, Wow! Signal reconstruction, φ² bridge diagram, anomaly inventory, and source index.

## 10. Limitations and Honest Constraints

Eccentricity distribution: The solar system eccentricity distribution is not uniform. The φ-power excesses may be partly explained by known dynamical structures (resonances, Oort Cloud pile-up). Comparison against N-body population synthesis models is needed.
Scoring weights: The harmonic scoring weights are researcher-defined, not derived from physics. Different weighting schemes would produce different rankings.
Post-hoc analysis: The temporal φ² ladder, velocity references, and scoring criteria were constructed after examining the data. None were pre-registered predictions. Future validation requires pre-specified tests against new data (particularly from the Vera Rubin Observatory).
528 Hz origin: The seed frequency 528.422 Hz originates from the solfeggio musical tradition and was hardcoded in the Aureon trading repository. It is not derived from first-principles physics. The φ² bridge calculation is valid arithmetic regardless of origin, but this is a degree of freedom.
Breakthrough Listen: The non-detection of technosignatures at 3I/ATLAS by three facilities (ATA, MeerKAT, GBT) favours a natural cometary body. The EPAS transient-burst hypothesis remains untested by matched-filter methods but the overall weight of evidence supports the null hypothesis.
Combined probability: The Sagittarius Convergence probability ranges from 1 in 8 million (conservative, with Bonferroni correction) to 1 in 80 billion (aggressive). Neither bound is conclusive.

## 11. Testable Predictions for the Vera Rubin Era

The Vera C. Rubin Observatory’s Legacy Survey of Space and Time (LSST), now operational, is expected to increase interstellar object detection rates from approximately one per decade to one every few months (Siraj & Loeb; Seligman et al.). Each new detection provides a new test of the harmonic framework. The following predictions are pre-registered here for future validation:
Prediction 1 — Eccentricity: The next confirmed interstellar object (4I) will have an eccentricity within 10% of a φ-power (φ⁻², φ⁻¹, φ⁰, φ¹, φ², or higher). Null: eccentricity is not near any φ-power.
Prediction 2 — Temporal: If 4I’s perihelion falls at N × φ² years from the Wow! Signal (±2.5%), with N integer, this strengthens the temporal ladder. Null: no N within 5%.
Prediction 3 — Velocity: The first ISO detected by Rubin will have v∞ within 10% of a φ-scaled multiple of 26.33 km/s (v‘Oumuamua). Null: velocity is unrelated.
These predictions are documented here with date (March 2026) to establish priority. Pass or fail, the results will constrain the framework.

## 12. Conclusion

The Harmonic Solar System Survey demonstrates that the φ²-scaled analysis framework developed for geological remote sensing applies to orbital parameter space, extracting structure from 109,000 objects across nine NASA/JPL databases. The principal finding — 7–9.9× eccentricity clustering at φ-powers in the comet population — is the strongest signal and requires comparison against dynamical population models to assess its significance.
The survey identifies 2003 RM (dark comet, e = φ⁻¹ ± 2.6%, Δt = 10×φ² ± 0.4%) and Ka‘epaoka‘awela (retrograde Jovian, e = φ⁻² ± 0.3%, possible interstellar capture) as the two strongest non-interstellar harmonic candidates. Five dark comets sit on both the non-gravitational acceleration list and the Sentry impact-risk database. The Wow! Signal stellar corridor contains 47 exoplanet systems, with two hosts (HD 179949 and K2-129) within 100 light-years.
The Vera Rubin Observatory will provide the definitive test. Three pre-registered predictions for the next interstellar object are documented here. The numbers are what they are. The data are open. The framework is falsifiable. The next discovery will either strengthen it or break it.

## 13. References


## 13.1 Interstellar Objects

Meech, K.J. et al. (2017). Nature 552, 378.
Kakharov, S. & Loeb, A. (2025). arXiv:2408.02739v5.
Loeb, A. (2025). Medium, Sep 29, 2025.
Jewitt, D. et al. (2025). NASA STScI.

## 13.2 Breakthrough Listen

Sheikh, S.Z. et al. (2025). arXiv:2512.18142.
Jacobson-Bell, B. et al. (2025). arXiv:2512.19763.
Pisano, D.J. et al. (2025). ATel 17499.

## 13.3 Dark Comets

Taylor, A.G. et al. (2024). Dark comets. Icarus.

## 13.4 Ka‘epaoka‘awela

Namouni, F. & Morais, M.H.M. (2018). MNRAS 477, L117.

## 13.5 Quasicrystals and φ in Physics

Shechtman, D. et al. (1984). PRL 53, 1951.
Coldea, R. et al. (2010). Science 327, 177.

## 13.6 Hydrogen Line

Hellwig, H. et al. (1970). IEEE Trans. Instrum. Meas. 19, 200.

## 13.7 Wow! Signal

Ehman, J.R. (1997). Big Ear Memorial Website.

## 13.8 HNC Framework

Leckey, G. (2026). EPAS Unified Architecture. Aureon Institute.
Leckey, G. (2026). HNC Harmonic LIDAR v2.0 with Aluminium Fluid Integration.
Leckey, G. (2026). The Sagittarius Convergence v2.0 (Corrected).

## 13.9 Databases

JPL Small-Body Database: ssd.jpl.nasa.gov
CNEOS Fireball Database: cneos.jpl.nasa.gov/fireballs
JPL Sentry: cneos.jpl.nasa.gov/sentry
NASA Exoplanet Archive: exoplanetarchive.ipac.caltech.edu
NOAA SWPC: services.swpc.noaa.gov
Gaia DR3 via VizieR: tapvizier.cds.unistra.fr

## 13.10 Future Surveys

Siraj, A. & Loeb, A. (various). Vera Rubin ISO detection predictions.
Seligman, D. et al. (various). Interstellar object population estimates.
