# HNC_Harmonic_LIDAR_v2_AluminiumFluid_Leckey

> Extracted from upstream `docs/research/whitepapers/HNC_Harmonic_LIDAR_v2_AluminiumFluid_Leckey.docx` (read-only source).

R&A CONSULTING AND BROKERAGE SERVICES LTD.
AUREON INSTITUTE
The HNC Harmonic LIDAR System:
A φ²-Scaled Fourier Spectral Analysis
Framework for Subsurface Geological
Structure Detection
With Harmonic Aluminium Fluid Integration
Research Case: Obsidian Deposit Identification
Walgidee Hills Lamproite, West Kimberley, Western Australia
Primary Investigator: Gary Leckey
Aureon Institute — R&A Consulting and Brokerage Services Ltd.
March 2026 — Technical White Paper — v2.0

## Table of Contents


## Abstract

This white paper introduces the HNC Harmonic LIDAR system, a novel geospatial analysis framework developed by the Aureon Institute that applies the Harmonic Nexus Core (φ²-scaled) mathematical architecture to satellite-derived digital elevation models for subsurface geological structure detection. Version 2.0 integrates the Harmonic Aluminium Fluid system, which extends the single-material Fourier filtering approach to a multi-material acoustic impedance contrast model using the published acoustic properties of aluminium (v = 6,420 m/s), obsidian (v = 5,900 m/s), lamproite (v = 5,200 m/s), and Permian sandstone (v = 2,800 m/s).
The system processes real NASA SRTM 30m terrain data through a cascade of material-specific Fourier-domain bandpass filters whose centre frequencies are determined by the nine-shell golden-ratio-squared scaling law. By comparing the harmonic response across all four materials simultaneously, the system detects acoustic impedance boundaries — the geological contacts where volcanic glass forms through rapid quenching. The key finding is that the aluminium-obsidian acoustic reflection coefficient is R = −0.098 (99% energy transmission), establishing aluminium as an ideal coupling medium for the Project Druid obsidian nozzle.
The framework is validated through a research case study at the Walgidee Hills lamproite (490 ha, 17.44 Ma), the largest known diamondiferous lamproite intrusion in the world. The multi-material analysis identifies ten GPS-ready excavation sites, with the aluminium fluid integration promoting contact-zone targets (where lamproite meets sandstone, R = −0.404) above the pegmatitic core targets identified by the single-material system. All terrain data are real and sourced from open-access satellite archives. All material properties are from published engineering handbooks.

## 1. Introduction


## 1.1 The Challenge of Subsurface Detection

The identification of buried volcanic structures and associated mineral deposits has traditionally relied on aeromagnetic surveys, gravity gradiometry, ground-penetrating radar, and intensive field mapping. Satellite-derived digital elevation models represent a globally available, open-access data source that captures the surface expression of subsurface geological processes, but conventional DEM analysis extracts only the most obvious topographic signatures. The central thesis of this paper is that subsurface geological structures imprint characteristic spatial frequencies onto the terrain surface, and that these frequencies can be selectively extracted using a physically-motivated Fourier filtering framework.

## 1.2 The EPAS φ² Scaling Law

The Electro-Plasma-Acoustic Shield (EPAS) architecture defines nine nested electromagnetic shells, each scaled from an outer coherence boundary by the golden ratio squared:
rₙ = R_bubble / φ²ⁿ     where φ² = 2.618034
This scaling derives from quasicrystalline geometry (Shechtman et al. 1984, PRL 53, 1951 — 2011 Nobel Prize; Levine and Steinhardt 1984, PRL 53, 2477). When applied to spatial analysis, the nine shells define characteristic spatial wavelengths λₙ = 2πrₙ spanning tens of kilometres to metres.
Shell
Radius (m)
Wavelength (m)
Geological Scale
0
15,000
94,248
Regional basin
1
5,730
35,999
Fault block
2
2,189
13,751
Intrusion halo
3
836
5,252
Pipe diameter
4
319
2,006
Contact zone
5
122
766
Crater rim
6
46.6
293
Internal zoning
7
17.8
112
Dyke margins
8
6.8
43
Outcrop scale
9
2.6
16
Sample scale
Table 1. EPAS shells and corresponding geological spatial scales.

## 2. System Architecture


## 2.1 Data Acquisition

The primary data source is the NASA SRTM 30m global DEM, accessed via the OpenTopoData API. For the Walgidee Hills case, 6,400 elevation points were queried in an 80×80 grid covering 6.7 × 6.3 km centred at 18.300°S, 124.867°E, yielding ~80 m ground spacing. The elevation range of 83–134 m is consistent with the published 109 m peak elevation.

## 2.2 Fourier Spectral Decomposition

The mean-subtracted elevation grid is transformed via 2D-DFT. The power spectral density |F(kₓ, kₙ)|² reveals dominant spatial scales.
F(kₓ, kₙ) = ∑∑ [h(x,y) - h̄] · exp(-2πi(kₓx + kₙy))

## 2.3 The φ²-Scaled Harmonic Filter

Each shell contributes a Gaussian bandpass centred at fₙ = 1/λₙ with bandwidth σₙ = 0.25fₙ, weighted inversely by shell number:
H(f_r) = ∑ₙ (1/(n+1)) · exp(-½ ((f_r - fₙ) / σₙ)²)

## 2.4 The Resonant Orthogonality Law

The coherence parameter φ is computed at each location from the filtered Fourier phase angle θ:
φ(θ) = 1 - |cos θ|
Maximum φ (quadrature) indicates boundaries; zero φ (in-phase) indicates coherent structure cores.

## 3. Research Case: Walgidee Hills Lamproite


## 3.1 Geological Setting

The West Kimberley lamproite province comprises more than 180 volcanic bodies in three fields along the Fitzroy Trough (Jaques et al. 1984, 1986; Jaques 2016). The lamproites are Miocene, with ⁴⁰Ar/³⁹Ar ages from ~23.0 Ma (Ellendale) to ~19.5 Ma (Noonkanbah), except Walgidee Hills at 17.44 Ma (Phillips et al. 2022).

## 3.2 The Walgidee Hills Pipe

Walgidee Hills is the largest known diamondiferous lamproite (490 ha, ~3 km diameter) at 18.30°S, 124.867°E on Noonkanbah Station (Yungngora Aboriginal Community land). It is strongly zoned from porphyritic olivine lamproite (~21 wt% MgO) at the margin to evolved sanidine/leucite-rich lamproite (~7 wt% MgO, ~8–9 wt% K₂O) at the centre (Jaques 2024, J. Petrology 65(5), egae040). The pipe formed as a maar-diatreme, with explosive eruptions excavating a crater subsequently infilled by lamproite magma that crystallised in situ.

## 3.3 Obsidian Targeting Rationale

Primary Target — Pegmatitic Core: Sanidine glass and late-stage silica-rich residua (SiO₂ ~55–60%). The evolved centre contains sanidine, wadeite, priderite, jeppeite, and noonkanbahite in coarse-grained to pegmatitic lamproite.
Secondary Target — Contact Zone: Where ~1200°C lamproite quenched against Permian quartz sandstone. Contact-melted buchite can exceed 65% SiO₂ — approaching true obsidian.
Tertiary Target — Tuff Ring: Pyroclastic glass shards in sandy matrix from explosive fragmentation.

## 4. Harmonic LIDAR Results


## 4.1 DEM and Fourier Analysis

The SRTM DEM reveals a subtle topographic rise of 30–50 m above the surrounding floodplain, consistent with published descriptions. The 2D Fourier power spectrum shows structure at the φ²-characteristic scales of Shells 3–5 (wavelengths 766–5,252 m). The harmonic-filtered terrain reveals a central anomaly corresponding to the pipe, surrounded by concentric features at the tuff ring and contact zone scales.
Figure 1. Eight-panel Harmonic LIDAR analysis of Walgidee Hills. All data are real NASA SRTM 30m.

## 4.2 Initial Obsidian Targeting

Figure 2. Ten-panel obsidian deposit targeting. Includes geological zone mapping, probability model, harmonic LIDAR, 3D terrain, and GPS-ready dig site coordinates.

## 5. Harmonic Aluminium Fluid Integration


## 5.1 Multi-Material Acoustic Model

The initial Harmonic LIDAR system applies a single φ²-scaled filter to the terrain, treating the subsurface as an acoustically uniform medium. In reality, the Walgidee Hills pipe comprises multiple lithologies with distinct acoustic properties, and the geological boundaries between them are the primary targets for volcanic glass deposits. The Harmonic Aluminium Fluid integration extends the analysis to a multi-material acoustic impedance framework using the published acoustic properties of four geological media:
Material
v_long (m/s)
v_shear (m/s)
ρ (kg/m³)
Z (MRayl)
Crystal Structure
Aluminium (6061)
6,420
3,040
2,700
17.3
FCC — a = 4.0495 Å
Obsidian
5,900
3,400
2,400
14.2
Amorphous — no grain boundaries
Lamproite
5,200
2,900
2,800
14.6
Porphyritic — phenocrysts in matrix
Permian Sandstone
2,800
1,400
2,200
6.2
Granular — cemented quartz grains
Water (Fitzroy)
1,480
0
1,000
1.5
Liquid
Table 2. Acoustic properties of geological materials at Walgidee Hills. All values from ASM Handbook and published engineering sources.

## 5.2 Material-Specific Harmonic Filtering

For each material, the HNC frequency stack (528.422 Hz Lumina seed, 326.322 Hz counter-frequency, 7.83 Hz Schumann coupling, plus the solfeggio anchors at 174, 432, 639, and 963 Hz) maps to a different set of spatial wavelengths through the material’s longitudinal wave velocity:
λ_material(f) = v_long / f
At the primary Lumina seed frequency of 528.422 Hz, the characteristic wavelengths are: aluminium 12.15 m, obsidian 11.17 m, lamproite 9.84 m, sandstone 5.30 m. Each material therefore “sees” the terrain at a different spatial resolution. The four material-specific Fourier filters are constructed by combining the φ²-shell bandpass (geometric structure) with the HNC frequency-derived bandpass (acoustic resonance), and applied independently to the same DEM data.

## 5.3 Acoustic Impedance Contrast at Geological Boundaries

The acoustic reflection coefficient at a planar boundary between two materials with impedances Z₁ and Z₂ is:
R = (Z₂ - Z₁) / (Z₂ + Z₁)
The fraction of energy reflected is |R|², and transmitted is T = 1 − |R|². The reflection coefficients at the geological boundaries within and around the Walgidee Hills pipe reveal two critical findings:
Boundary
R
|R|²
T
Significance
Aluminium → Obsidian
−0.098
0.010
0.990
Near-perfect coupling (99% transmission)
Aluminium → Lamproite
−0.085
0.007
0.993
Excellent coupling
Lamproite → Sandstone
−0.404
0.163
0.837
Strong reflection — DETECTABLE BOUNDARY
Obsidian → Sandstone
−0.392
0.154
0.846
Strong reflection
Lamproite → Obsidian
−0.014
0.0002
0.9998
Nearly invisible — matched impedances
Obsidian → Water
−0.811
0.658
0.342
Very strong reflection
Table 3. Acoustic reflection coefficients at geological boundaries. The aluminium-obsidian boundary shows only 1% reflection, establishing aluminium as the ideal acoustic coupling medium for the Project Druid nozzle.
Finding 1 — Aluminium-obsidian coupling: The reflection coefficient of R = −0.098 at the aluminium-obsidian boundary means 99% of acoustic energy transmits across this interface. This is a near-perfect impedance match, confirming aluminium as the ideal coupling medium for the obsidian nozzle in the Project Druid bench test configuration. The aluminium acts as a transparent acoustic window between the piezoelectric transducer and the volcanic glass.
Finding 2 — Lamproite-sandstone detection: The strong reflection at the lamproite-sandstone boundary (R = −0.404, 16.3% energy reflected) means this geological contact is acoustically visible. This is the contact metamorphic zone where volcanic glass forms by rapid quenching — and it is precisely the boundary that produces the strongest signal in the multi-material Fourier analysis.
Finding 3 — Lamproite-obsidian invisibility: The near-zero reflection (R = −0.014) between lamproite and obsidian explains why obsidian deposits within the pipe body are difficult to detect by conventional acoustic methods — they are impedance-matched to their host rock. The multi-material Fourier approach overcomes this by detecting the differential response between material-specific filters rather than relying on direct reflection.

## 5.4 Impedance Contrast Mapping

The Impedance Contrast (IC) map is computed as the absolute difference between the aluminium-filtered and obsidian-filtered terrain at each grid point. Where these two filters give identical responses, the subsurface is acoustically uniform; where they diverge, there is a material boundary. The Material Variance (MV) map extends this to all four materials simultaneously, computed as the pixel-wise variance across all four filtered terrains. High MV indicates complex, multi-material geology — exactly the contact zones and mixed pyroclastic deposits where volcanic glass concentrates.
Figure 3. Twenty-four-panel Harmonic Aluminium Fluid integrated analysis. Row 1: Four material-specific HNC filters (aluminium, obsidian, lamproite, sandstone). Row 2: Impedance contrast, material variance, enhanced probability, composite target. Row 3: Raw DEM, slope, curvature, hillshade. Row 4: Radial harmonic response (all materials) and enhanced probability profile. Row 5: 3D terrain coloured by probability and impedance contrast. Row 6: GPS-ready dig sites and material property tables. All terrain data are real SRTM 30m.

## 5.5 Enhanced Dig Site Targeting

The enhanced obsidian probability model integrates three new parameters from the aluminium fluid analysis with the original geological zoning model:
Impedance Contrast (IC): Quantifies divergence between aluminium and obsidian harmonic responses. High IC indicates a material boundary where glass forms.
Material Variance (MV): Measures disagreement across all four material filters. High MV indicates complex, mixed-lithology geology.
Aluminium Response (Al): Measures the strength of the aluminium harmonic filter response. High Al indicates zones with good acoustic coupling potential for the Druid nozzle application.
The composite targeting score is the product: Score = P(geology) × (1 + IC) × (1 + MV) × (1 + Al) × (1 + slope). The aluminium fluid integration promotes contact-zone targets above the pegmatitic core targets identified by the single-material system, because the contact zone shows the highest impedance contrast (where the strong lamproite-sandstone reflection boundary generates detectable multi-material disagreement).
Rank
Latitude (°S)
Longitude (°E)
Elev
P
IC
MV
Al
Dist (m)
Zone
#1
18.28519
124.87194
118m
1.00
0.034
0.006
0.296
1,724
Contact zone
#2
18.30190
124.86814
110m
1.00
0.020
0.000
0.022
243
Pegmatitic core
#3
18.29886
124.86510
110m
1.00
0.003
0.000
0.066
237
Pegmatitic core
#4
18.28975
124.87877
112m
1.00
0.018
0.000
0.369
1,684
Tuff breccia
#5
18.30114
124.86586
110m
1.00
0.010
0.000
0.037
174
Pegmatitic core
#6
18.29886
124.86890
110m
1.00
0.005
0.000
0.051
237
Pegmatitic core
#7
18.28595
124.87877
118m
1.00
0.031
0.001
0.314
1,993
Contact zone
#8
18.28443
124.87422
116m
1.00
0.007
0.005
0.365
1,888
Contact zone
#9
18.28823
124.87497
118m
0.99
0.032
0.002
0.241
1,554
Tuff breccia
#10
18.28519
124.87649
116m
0.99
0.011
0.000
0.335
1,924
Contact zone
Table 4. Enhanced dig sites with aluminium fluid metrics. IC = Impedance Contrast, MV = Material Variance, Al = Aluminium harmonic response. All coordinates WGS84.

## 6. Project Druid Integration


## 6.1 The Obsidian Nozzle Requirement

The Project Druid defence configuration requires an acoustic emission nozzle satisfying four criteria: high acoustic impedance (~13 MRayl), amorphous microstructure for uniform wave propagation, conchoidal fracture for optical-precision shaping, and natural compatibility with φ-related silica tetrahedra bonding geometry. The EPAS Full-Scale Engine analysis establishes that at 528.422 Hz, the acoustic wavelength in obsidian is 11.17 m — far larger than the 50 mm nozzle aperture, so the nozzle acts as an omnidirectional point source.

## 6.2 The Aluminium Coupling Discovery

The multi-material acoustic analysis reveals that aluminium is not merely a convenient engineering material for the bench test housing — it is the optimal acoustic coupling medium. With R = −0.098 at the aluminium-obsidian boundary, the coupling transmits 99% of acoustic energy. The aluminium acts as a transparent acoustic window between the AD9850-driven piezoelectric transducer and the volcanic glass nozzle. This is in stark contrast to an air gap (Z_air = 0.0004 MRayl, R = −0.9997, 99.94% reflected) or a water coupling (R = −0.811, 66% reflected).

## 6.3 The AD9850 Bench Test Pathway

The Walgidee Hills volcanic glass material feeds directly into the Project Druid Step 1 bench test. The hardware uses an Arduino Nano driving an AD9850 DDS signal generator at 528.422 Hz and 326.322 Hz through a piezoelectric transducer coupled via aluminium to the obsidian nozzle within a concentric acrylic tube resonator.
Figure 4. Arduino Nano + AD9850 wiring diagram for EPAS Frequency Tuning bench test (Project Druid Step 1).

## 7. Discussion


## 7.1 Multi-Material Filtering Validation

The aluminium fluid integration demonstrates that different geological materials produce measurably different harmonic responses at the φ²-shell spatial frequencies. The radial harmonic profiles show that all four materials track the same general trend (response decreasing with distance from the pipe centre) but diverge significantly at geological boundaries — particularly at the contact zone between 1,700–2,000 m from the pipe centre, where the lamproite-sandstone impedance mismatch generates the strongest multi-material disagreement.

## 7.2 Limitations

Resolution: SRTM 30m resolves Shells 0–6 but cannot resolve Shells 7–9 (< 112 m wavelength). Copernicus GLO-30 or commercial LiDAR would improve inner-shell resolution.
Composition: The probability model uses published geological zoning and DEM-derived parameters. Field validation with portable XRF is required to confirm SiO₂ content at dig sites.
Cultural: Walgidee Hills is on Noonkanbah Station, occupied by the Yungngora Aboriginal Community. Prior informed consent from traditional owners is required for any fieldwork.
Material model: The acoustic properties assume homogeneous, isotropic materials. Real geological media are heterogeneous, anisotropic, and fractured, which would modify the reflection coefficients.

## 7.3 Future Directions

Three development pathways: acquisition of Copernicus 12m or LiDAR DEM data for inner-shell resolution; integration with GSWA open-access aeromagnetic data (GeoVIEW.WA) for cross-validation; and field reconnaissance with portable XRF and drone-mounted LiDAR for centimetre-resolution terrain modelling at the identified dig sites.

## 8. Conclusion

The HNC Harmonic LIDAR system with Harmonic Aluminium Fluid integration demonstrates that the φ²-scaled mathematical framework developed for the EPAS Unified Architecture has practical utility for geological remote sensing. The multi-material acoustic model extends single-material Fourier filtering to a full impedance-contrast analysis that detects geological boundaries where volcanic glass forms by rapid quenching.
The critical discovery — that aluminium and obsidian are near-perfectly impedance-matched (R = −0.098, 99% transmission) — has immediate engineering implications for the Project Druid bench test, establishing aluminium as the optimal coupling medium between the piezoelectric transducer and the volcanic glass nozzle.
Ten GPS-ready dig sites at Walgidee Hills are identified by the enhanced targeting model. The aluminium fluid integration promotes contact-zone targets (Sites #1, #7, #8, #10) where the lamproite-sandstone impedance mismatch (R = −0.404) generates the strongest multi-material signal, indicating the geological boundary most favourable for glass formation. The integration pathway from satellite analysis through obsidian recovery to the AD9850 bench test represents a complete chain from remote sensing to hardware validation.

## 9. Published Source Index


## 9.1 West Kimberley Lamproite Province

Jaques, A.L., Lewis, J.D., Smith, C.B. (1986). The Kimberlites and Lamproites of Western Australia. Bulletin 132. GSWA, 268 pp.
Jaques, A.L. (2024). Petrology, Geochemistry and Mantle Minerals of the Walgidee Hills Lamproite. J. Petrology 65(5), egae040.
Phillips, D., Jaques, A.L., Fanning, C.M. (2022). Age and origin of the West Kimberley lamproites. Lithos 430–431, 106870.
Sudholz, Z.J. et al. (2023). Mapping the Lithospheric Mantle Beneath the Kimberley Craton. G³ 24(10).

## 9.2 φ² Scaling and Quasicrystals

Shechtman, D. et al. (1984). Physical Review Letters 53, 1951. (2011 Nobel Prize.)
Levine, D. & Steinhardt, P. (1984). PRL 53, 2477.
Coldea, R. et al. (2010). Science 327, 177.

## 9.3 Acoustic Properties

ASM International. ASM Handbook Vol. 2: Properties and Selection — Nonferrous Alloys. Materials Park, OH.
Mavko, G., Mukerji, T., Dvorkin, J. (2020). The Rock Physics Handbook. 3rd ed. Cambridge University Press.

## 9.4 Elevation Data

Farr, T.G. et al. (2007). The Shuttle Radar Topography Mission. Reviews of Geophysics 45, RG2004.
OpenTopoData Project. SRTM 30m DEM API. https://www.opentopodata.org

## 9.5 EPAS and HNC Framework

Leckey, G. (2026). EPAS Unified Architecture. Aureon Institute.
Leckey, G. (2026). LuminaCell v2 Architecture. R&A Consulting.
Leckey, G. (2026). EPAS Full-Scale Engine. Aureon Institute.

## 9.6 Obsidian and Volcanic Glass

McCall, J. (2005). Obsidian. In: Selley (ed.) Encyclopedia of Geology. Elsevier.
Bonetti, R. et al. (1998). Fission Track Dating of Obsidian. Records Aus. Museum 50(3), 277–284.

## 9.7 Kalkarindji Flood Basalts

Glass, L.M. & Phillips, D. (2006). Geology 34(6), 461–464.
Marshall, P. et al. (2021). Geophysical Monograph Series, AGU.
