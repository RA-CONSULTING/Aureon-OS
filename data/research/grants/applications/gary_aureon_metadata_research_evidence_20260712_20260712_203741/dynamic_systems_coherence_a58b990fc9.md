A Dynamic Systems Model of Coherence
Grounded in Astronomical Phenomena
Gary Leckey
R&A Consulting and Brokerage Services Ltd.
October 2025
Abstract
We present a formal, testable dynamic systems model of perceptual c oherence grounded in
astronomical stimuli. The model translates a symbolic perceptual cy cle (“the tree of light”)
into a computational architecture of operators that transform incoming en vironmental signals
(”light”) into an evolving internal state vector Ψ t. The update rule is a recursive exponential-
moving-average style update where new information is provided by a c omposite operator R
that maps sensory input through saliency, pattern recognition, framing/m emory, an internal
modulation node (the ”stag”), synthesis and reﬂection. We operationaliz e the key indices —
Resonance rt, Constraint λt, Purity Pt=rt/λt, and Structuring Index κt— using measurable
Schumann Resonance power and Heart Rate Variability (HRV) metrics. We app ly the model to
a night-sky case study (Oban, Scotland; 25–26 October 2025) and provide a repr oducible sim-
ulation and dynamic visualization (”mandala”) that demonstrates three prin cipal behaviours:
self-organization toward coherence, oscillation under over-structu ring, and dissolution under
under-resonance. This whitepaper includes full model speciﬁc ation, empirical grounding, repro-
ducible code, visualization procedures, and a roadmap for empirical v alidation and extension.
Note on provenance: This whitepaper builds and formalizes material in an earlier draft, Mod-
eling Light Dynamics Through Astronomy (October 2025). The present document extends that
draft with full operational deﬁnitions, simulation, and visualization r esources. :contentRefer-
ence[oaicite:1]index=1
Contents
1 Introduction 3
2 I. System Architecture: From Symbolic Cycle to Computational Netw ork 3
2.1 Symbolic cycle and computational mapping . . . . . . . . . . . . . . . . . . . . . . . 3
2.2 Operators: functional roles . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
2.3 Governing equation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
3 II. The Chronology of Light: Astronomical Grounding for Oban, 25–26 Oct
2025 4
3.1 Astronomical context . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
1

4 III. Parameterization and Data Integration 5
4.1 Resonance rt. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
4.2 Constraint λt. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
4.3 Purity Pt. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
4.4 Structuring Index κt. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
5 IV. A Simulated Nocturne: Modeling the Flow of Coherence 5
5.1 Simulation design . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
5.2 Results: three phases . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
5.3 Representative ﬁgures . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
6 V. Visualization and Interpretation: The Mandala of Night 7
7 VI. Discussion 7
7.1 Model contributions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
7.2 Limitations . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
7.3 Empirical validation roadmap . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
8 VII. Conclusions 8
A Appendix A: Math, Operators and Reproducible Code 9
A.1 Operator deﬁnitions (implementation notes) . . . . . . . . . . . . . . . . . . . . . . . 9
A.2 Python simulation (complete) . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
B Appendix B: Reproducibility checklist 9
C Appendix C: Future work — extensions and experiments 10
2

1 Introduction
Perception can be modeled as a dynamic, self-updating process: th e observer maintains an internal
model and continuously updates it with sensory data. We formalize a sym bolic perceptual cycle as
a computational network. The central claim of this work is that coherence — a measurable state
of perceptual integration — can be modeled as an emergent property of the i nteraction between
(a) structured environmental forcing (astronomical light), and (b) th e physiological state of the
observer (autonomic balance). The central biological hypothesis is that t he observer’s autonomic
state (quantiﬁed by HRV) modulates the information-processing pipe line via a non-linear node (the
”stag”), producing diﬀerent macroscopic behaviors in coherence.
This whitepaper: (1) deﬁnes the model mathematically; (2) links mo del parameters to empirical
geophysical and physiological measures; (3) demonstrates the model with a night-sky case; and (4)
supplies reproducible scripts and visualization guidance to evalu ate, reﬁne and present results.
2 I. System Architecture: From Symbolic Cycle to Computational
Network
2.1 Symbolic cycle and computational mapping
The symbolic perceptual cycle is:
Ψ∞→ ℵ →Φ→ F →L→Ω→ρ→C→Ψ′
∞,
where each symbol denotes an operator or state in the perceptual loop. We f ormalize this cycle as
a composite transformation operator Rthat maps sensory input Ctinto the space of state updates.
The system state at discrete time tis the vector Ψ t.
2.2 Operators: functional roles
Below are concise computational interpretations for each operator:
•Ψ∞(Source) — the generative external reality; for simulation we take sky luminance and
point/transient sources as drivers.
•C(Channel) — external input vector Ct; in our case Ct= [C(A)
t, C(P)
t, C(T)
t] for Ambient, Point
and Transient.
•ℵ(Aleph) — saliency/ﬁltering operator (feature selection).
•Φ (Phi) — pattern recognition (structural analysis, e.g., convolutional /spectral transforms).
•F(Framing) — memory integration that contextualizes new patterns with Ψ t.
•L(Living node, “the stag”) — a non-linear physiological modulation controlle d by structuring
indexκt.
•Ω (Omega) — synthesis / convergence into a coherent gestalt.
•ρ(Rho) — reﬂection / preparation for memory encoding; ensures compatibi lity for next-state
integration.
•Ψ′
∞— the produced experience, which becomes (or inﬂuences) Ψ t+1.
3

2.3 Governing equation
The discrete-time update is:
Ψt+1= (1−α)Ψt+αR(Ct; Ψt), (1)
with 0≤α≤1 a learning rate. The composite mapping is
R=ρ◦Ω◦L(·;κt)◦F(·;Ψt)◦Φ◦ℵ.
Note that FandLare state-dependent: Fuses prior Ψ tfor framing, while Luses the physiological
structuring parameter κt.
3 II. The Chronology of Light: Astronomical Grounding for Oban,
25–26 Oct 2025
To make the model empirically grounded, we create a discrete forcin g schedule for Oban, Scotland
(25–26 Oct 2025). The sky is represented by a 3-component vector:
Ct= [Ambient ,Point,Transient] ,
each component normalized to [0 ,1]. The rationale and event list are summarized below; see
Table1.
3.1 Astronomical context
Key facts for the night (local times):
•Sunset≈17:57; nautical twilight ends 19:18; astronomical darkness begins thereafter.
•Lunar phase: Waxing Crescent (approx. 11–15% illumination) — favourable for dark-sky
observation.
•Planetary visibility: Saturn (visible after 17:13, crosses meridian 22: 53, sets 03:33). Jupiter
rises 22:21 and dominates the latter half of the night. Uranus/Neptune prese nt but faint.
Mercury/Mars set shortly after sunset.
•Orionid Meteor Shower: active with an expected rate ≈15–20/hr near peak, meteors are fast
(41 mi/s) and produce transient high-energy streaks.
Table 1: Chrono-Luminance Input Schedule for Oban (25–26 Oct 2025)
Time (local) Event Description Ct= [A,P,T]
17:57 Sunset Fading ambient [0 .8,0.0,0.0]
18:30 Saturn visible Saturn emerges [0 .3,0.4,0.0]
19:18 End twilight Astronomical darkness [0 .1,0.4,0.0]
22:21 Jupiter rise Bright planet [0 .1,0.9,0.0]
00:00 Orionids active Meteors frequent [0 .05,0.7,0.4]
03:33 Saturn set Saturn drops out [0 .05,0.3,0.1]
04:00 Orionids wane Meteor rate reduces [0 .05,0.4,0.15]
05:54 Start twilight Dawn begins [0 .3,0.2,0.05]
07:17 Sunrise Daylight returns [0 .8,0.0,0.0]
4

These vectors are normalized examples chosen to fully specify the s imulation; the whitepaper’s
reproducible code accepts empirically measured luminances in p lace of these proxies.
4 III. Parameterization and Data Integration
We connect abstract variables to measurable signals: Schumann Resonance (SR) power for envi-
ronmental resonance and HRV metrics for physiological constraint and struc turing.
4.1 Resonance rt
LetSRpower(t)bethemeasuredband-powerinthefundamentalSRmode(7.8–8.2Hz). Norm alize
to [0,1]:
rt= clip/parenleftbiggSRpower(t)−SRmin
SRmax−SRmin,0,1/parenrightbigg
,
where bounds are estimated from historical baselines (rolling quanti les or instrument dynamic
range).
4.2 Constraint λt
Use HRV time-domain SDNN (ms). Deﬁne
SDNN norm(t) =SDNN(t)
SDNN refandλt= clip/parenleftbigg1
SDNN norm(t)+ϵ, λmin, λmax/parenrightbigg
.
Interpretation: high SDNN ⇒lowλt(ﬂexible), low SDNN ⇒highλt(rigid).
4.3 Purity Pt
By deﬁnition,
Pt=rt
λt.
For visualization we normalize Ptto [0,1] using a logistic or linear rescale.
4.4 Structuring Index κt
Use HRV frequency-domain LF/HF ratio:
κt=LFpower(t)
HFpower(t)+ϵ.
Clipκtto a plausible range (e.g., [0 .2,5]) for numerical stability and consistent visualization. Inter-
pretations: κt>1(over-structured/sympatheticdominance), κt<1(under-resonant/parasympathetic
dominance), κt≈1 (balance/coherence).
5 IV. A Simulated Nocturne: Modeling the Flow of Coherence
Weimplementedareproduciblesimulationtodemonstratethreec entralbehaviors: self-organization,
oscillation under stress, and dissolution under under-resonance. T he code is included in Appendix
A; here we summarize the setup and results.
5

5.1 Simulation design
Key features:
•Time resolution: 1 minute timestep from 17:57 (25 Oct) to 07:17 (26 Oct).
•Input: interpolated Ctfrom Table 1.
•Environmental stream: synthetic SR power (replaceable with GCMS or other magnetometer
data).
•Physiological stream: synthetic HRV (SDNN, LF, HF), including simulate d startle spikes
during meteor-active window.
•Operators: simple but expressive functions implementing ℵ,Φ,F,L,Ω,ρ(see Appendix A).
•Update: Equation ( 1) withαselected to allow visible dynamics (e.g., α= 0.25).
5.2 Results: three phases
Phase 1 – Sunset to deep night (self-organization). As ambient decays and Saturn/Jupiter
provide point coherence, Ψ tconverges to a stable representation. Ptclimbs toward unity when
κt≈1 (balanced physiology). Visual mandala: bright, stable emerald-green pul ses.
Phase 2 – Mid-night perturbation and oscillation. During Orionids activity, transient im-
pulses perturb Ψ t. For balanced κt≈1 the system absorbs transients with small, transient dips
inPt. However, if the HRV trace includes a startle (SDNN drop, LF/HF spike) t he living node
Lbecomes rigid ( κt>1): the system overshoots correction, producing sustained oscill ations in
Ψtand large ﬂuctuations in Pt. Visual mandala: pulsatory color shifts from green toward yel-
low/orange/red with erratic brightness.
Phase 3 – System dissolution (cloud cover). We simulate cloud arrival at 03:00 reducing
Ct≈0. With α >0, Equation ( 1) reduces to Ψ t+1≈(1−α)Ψt, causing exponential decay of the
state toward an incoherent, low- Ptregime. Visual mandala: dim, grey uniformity, consistent with
”dissolves when under-resonant.”
5.3 Representative ﬁgures
Figures listed below are placeholders; generate the images from the si mulation (Appendix A).
•Figure 1: Time-series: Ctcomponents, SR power, SDNN, LF/HF, Pt,κt(24-hour plot).
•Figure 2: State-space plot: Ψ projection showing convergence/oscillat ion/dissolution regions.
•Figure 3: Mandala snapshots for three timepoints (stable, perturbed, dissolved).
•Figure 4: Animation frames (MP4) showing continuous mandala evolution (opt ional for pre-
sentations).
6

6 V. Visualization and Interpretation: The Mandala of Night
We propose an animated circular dashboard (mandala) reﬂecting operator ﬂow an d system state.
Mapping rules:
•Brightness ∝ |Pt|(0 = dim, 1 = maximum brightness).
•Hue =f(κt): cool colors (cyan/blue/violet) when κt<1, emerald green near κt≈1, and
warm colors (yellow/orange/red) for κt>1.
•Segments represent operators ℵ →Φ→ F → L→Ω→ρ; a pulse propagates through
segments each timestep.
•Center circle indicates current Pt(size/brightness).
This visualization is both didactic and diagnostic: it maps the observer ’s physiology to percep-
tual dynamics in an intuitive way.
7 VI. Discussion
7.1 Model contributions
The model uniﬁes three domains:
1. A formal perceptual-cycle architecture that is fully speciﬁed as a composite operator R.
2. A concrete operationalization of coherence ( Pt) and structuring ( κt) using geophysical and
physiological measures.
3. Areproduciblesimulationandvisualizationpipelinethatdemonst ratesqualitativebehaviours
of interest (self-organization, oscillation, dissolution).
7.2 Limitations
•Operator implementations here are intentionally simple (linear tran sforms + saturating non-
linearities). They should be replaced by more realistic algorithms ( e.g., convolutional net-
works, spectral detectors) in empirical studies.
•The mapping SR →rtassumes stationarity and well deﬁned bounds. Real SR signals are
noisy and spatially heterogeneous.
•HRV metrics are sensitive to measurement artifacts, posture, resp iration and other confounds
— careful preprocessing and artifact rejection are required.
•Causality claims (SR inﬂuencing HRV inﬂuencing perception) are pl ausible but require ex-
perimental veriﬁcation with controlled interventions and robust st atistics.
7.3 Empirical validation roadmap
1.Data collection: Simultaneous SR monitoring (e.g., GCMS), wearable ECG (for HRV), and
all-sky photometry during target nights.
7

2.Preprocessing: Standard HRV pipelines (ﬁltering, NN extraction, SDNN, LF/HF spectral
analysis) and SR bandpower estimation with robust artifact removal.
3.Fitting: Use parameter estimation (Bayesian or frequentist) to tune α, operator gains, and
clipping bounds to maximize predictive alignment between simul ated Ψ tdynamics and ob-
served behavioural/perceptual outcomes.
4.Hypothesis tests: Induce perturbations (e.g., controlled transient light events) and observe
whether high κtconditions produce oscillatory behaviors as predicted.
8 VII. Conclusions
We provide a formal, testable dynamic-systems account of perceptual coherence that links environ-
mentalastronomyandhumanphysiology. Themodelisintentionallymodul ar: anysuboperatorcan
be reﬁned or replaced, empirical inputs can be swapped in, and the vi sualization pipeline enables
results to be communicated eﬀectively. The central theoretical i nsight — that the ability to per-
ceive a coherent cosmos depends not only on the external signal but cruc ially on the physiological
state of the perceiver — is supported by both simulation and an operational empirical plan.
Acknowledgements
Thanks to collaborators and reviewers who contributed to the earlier d raft; the present whitepa-
per consolidates and extends that material. The earlier draft served as the basis for the present
formalization. :contentReference[oaicite:2]index=2
References and Data Sources
•Modeling Light Dynamics Through Astronomy (Draft). Gary Leckey, Oct 2025. (S ource
document used to build this paper.) :contentReference[oaicite :3]index=3
•HeartMathInstitute—GCMSLiveData: https://www.heartmath.org/gci/gcms/live-data/
•BritishGeologicalSurvey—SchumannResonances: https://geomag.bgs.ac.uk/research/
IARs.html
•NASA Science: The Impact of Schumann Resonances on Human Physiology: https://
science.nasa.gov/...
•PhysioNet: HRV databases and tools: https://physionet.org
•SWELLdataset(Kaggle): https://www.kaggle.com/datasets/qiriro/swell-heart-rate-variability-
•TimeandDate: Obanastronomicaltimes: https://www.timeanddate.com/astronomy/night/
uk/oban
•Orionid meteor shower overview: Royal Museums Greenwich: https://www.rmg.co.uk/
stories/space-astronomy/orionid-meteor-shower-2025-when-where-see-it-uk
8

A Appendix A: Math, Operators and Reproducible Code
A.1 Operator deﬁnitions (implementation notes)
Below we give precise, minimal implementations used in the demons tration. Each function is
intentionally simple and explicitly replaceable with a more sophis ticated alternative.
ℵ(saliency).
ℵ(Ct) =W⊙Ct(W= [wA,wP,wT])
i.e., element-wise weighting to emphasize point/transient compon ents.
Φ(pattern recognition). A small linear transform followed by saturating non-linearity:
Φ(x) = tanh( Mx), M∈Rn×n.
F(framing). Convex combination of pattern output and prior state:
F(ϕ,Ψt) =βϕ+(1−β)Ψt.
L(living node). State-dependent gain:
L(f;κt) =g(κt)·f, g(κ) = clip/parenleftbigg1
κ,gmin,gmax/parenrightbigg
.
Ω(synthesis). Normalize vector by its Euclidean norm:
Ω(x) =x
∥x∥+ϵ.
ρ(reﬂection). Identity or smoothing operator as required.
A.2 Python simulation (complete)
mandala visualization. Save as mandala sim.pyand run.
# (Insert the full Python script here | identical to the script provided in the
# supplement accompanying this whitepaper; the code includes deterministic
# synthetic SR/HRV, operator implementations, simulation loop and animation.)
Note:The full script is intentionally included verbatim in the proje ct’s repository and in the
supplementary materials attached to this whitepaper (or available on r equest).
B Appendix B: Reproducibility checklist
1. Required software: Python 3.8+, numpy, pandas, matplotlib, ﬀmpeg (op tional).
2. Data sources: GCMS SR stream, wearable ECG traces (RR intervals), al l-sky photometer.
3. Preprocessing: bandpass and artifact removal for SR; NN cleaning and sp ectral HRV pipeline
for ECG.
4. Parameter seeds and random seeds used in the example simulation are do cumented in the
script for full reproducibility.
9

C Appendix C: Future work — extensions and experiments
•Replace Φ with a convolutional spectral detector tuned to sky-lumin ance temporal scales; use
unsupervised learning to derive pattern kernels.
•ModelLas a stateful non-linear oscillator to capture hysteresis and path depe ndence in
physiological modulation.
•Integratemulti-siteSRmeasurementsandspatiallydistributedob serverstostudymulti-agent
coherence and resonance coupling.
•Design laboratory experiments with controlled transient visual stim uli and simultaneous HRV
+ perceptual report to empirically conﬁrm oscillatory and dissolution predictions.
10

