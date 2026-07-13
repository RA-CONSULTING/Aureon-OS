# Open Source Ionospheric Data Sources
## Analysis Report | April 7, 2026

---

## Executive Summary

This report catalogs **13+ publicly accessible ionospheric monitoring systems** providing real-time and archival data suitable for independent anomaly detection and verification.

**Key Finding:** Multiple independent open-source systems confirm comprehensive ionospheric monitoring capability exists globally. Data is accessible for anomaly detection, correlation analysis, and independent verification.

---

## Real-Time Ionospheric Monitoring

### 1. GIRO/GAMBIT (Global Ionospheric Radio Observatory)
- **URL:** https://giro.uml.edu/GAMBIT
- **Description:** Global Assimilative Model of Bottomside Ionosphere Timeline
- **Data Types:** IRTAM 3D coefficients, foF2, hmF2, B0, B1
- **Access:** Open academic-use, guest accounts available
- **Coverage:** 69+ ionosonde stations worldwide
- **Real-Time:** 3-day delay for open data, subscription for real-time

### 2. HAARP Diagnostic Suite
- **URL:** https://haarp.gi.alaska.edu/diagnostic-suite
- **Description:** University of Alaska Fairbanks ionospheric observatory
- **Data Types:**
  - Ionosonde (vertical sounding)
  - Oblique ionosonde (Cordova to Delta Junction)
  - Fluxgate magnetometer
  - Riometer
- **Access:** Public real-time data feeds
- **Coverage:** Gakona, Alaska (62.4°N, 145.2°W)
- **Real-Time:** Yes - continuous passive monitoring

### 3. Mirrion 2 (NOAA NCEI)
- **URL:** https://www.ncei.noaa.gov/products/space-weather/legacy-data/mirrion-2-real-time-ionosonde
- **Description:** Real-time ionosonde data mirror system
- **Data Types:** Latest ionograms, MUF3000 maps, global station maps
- **Access:** Public FTP and web interface
- **Coverage:** 100+ global ionosonde stations
- **Real-Time:** Yes

### 4. SGO Ionosonde (Finland)
- **URL:** https://www.sgo.fi/Data/Ionosonde/ionData.php
- **Description:** Sodankylä Geophysical Observatory
- **Data Types:** HFTI plots, HTI plots, foE, foF2
- **Access:** Free for scientific/educational use
- **Coverage:** Northern Finland (67.4°N, 26.6°E)
- **Real-Time:** Daily updates

### 5. WALDO VLF Database
- **URL:** https://waldo.world
- **Description:** Worldwide Archive of Low-Frequency Data and Observations
- **Data Types:** VLF amplitude data, transmitter-receiver pairs
- **Access:** Open access (MATLAB format, CSV conversion tools available)
- **Coverage:** Global VLF network
- **Real-Time:** Archive with recent data

---

## Schumann Resonance Monitoring

### 1. Space Observing System (Tomsk, Russia)
- **URL:** https://schumannresonancedata.com/
- **Description:** Real-time Schumann resonance monitoring
- **Data Types:** SR spectrograms, amplitude data, frequency tracking
- **Access:** Public web interface
- **Coverage:** Tomsk, Russia (56.5°N, 85.0°E)
- **Real-Time:** Hourly updates

### 2. GeoCenter.info
- **URL:** https://geocenter.info/en/monitoring/schumann
- **Description:** Schumann resonance online monitoring
- **Data Types:** Frequency plots, amplitude plots, Q-factor plots
- **Access:** Public web interface
- **Coverage:** Tomsk region
- **Real-Time:** Continuous

### 3. Disclosure News Italy
- **URL:** https://www.disclosurenews.it/schumann-resonance-today/
- **Description:** Schumann resonance daily updates and analysis
- **Data Types:** Daily SR reports, power levels, frequency variations
- **Access:** Public web updates
- **Coverage:** Global
- **Real-Time:** Daily updates

---

## Space Weather & GNSS Data

### NOAA SWPC
- **URL:** https://www.swpc.noaa.gov
- **Data:** Solar wind, magnetometer, Kp index, aurora forecasts
- **Real-Time:** Yes

### NASA iSWA
- **URL:** https://iswa.gsfc.nasa.gov
- **Data:** Enlil solar storm model, magnetosphere models
- **Real-Time:** Yes

### TechTIDE
- **URL:** http://www.tech-tide.eu/
- **Data:** Traveling Ionospheric Disturbance (TID) tracking
- **Real-Time:** Yes

### IGS (International GNSS Service)
- **URL:** https://igs.org/
- **Data:** VTEC maps, GNSS data, ionospheric products
- **Real-Time:** Yes

---

## Anomaly Detection Capabilities

### Ionosonde Methods
- Spread-F detection (HA419-IonogramSet ML dataset available)
- Critical frequency variations (foF2, foE)
- Virtual height anomalies
- D-region absorption (DRAP model)

### VLF Methods
- Amplitude variations from transmitter-receiver pairs
- Sudden ionospheric disturbances (SIDs)
- Solar flare effects

### Schumann Resonance Methods
- Frequency deviations from 7.83 Hz baseline
- Amplitude spikes (Power levels)
- Harmonic anomalies (14, 20, 26, 33 Hz)

### Magnetometer Methods
- Kp index variations
- Local magnetic field fluctuations
- Auroral electrojet activity

---

## Key Open Datasets

### HA419-IonogramSet-2025
- **Source:** Hainan Fuke ionosonde station
- **Coverage:** 2002-2016 (150,000 ionograms)
- **Categories:** 5-class Spread-F classification
- **Access:** https://doi.org/10.57760/sciencedb.26826

### WALDO VLF Repository
- **Maintained by:** University of Colorado, Georgia Tech, Stanford
- **Data:** Transmitter-receiver VLF amplitude pairs
- **Access:** https://waldo.world

---

## Conclusion

**The ionosphere is extensively monitored by open-source systems.**

Any significant anomaly would be detectable through:
1. Multiple independent ionosonde networks
2. Global VLF monitoring
3. Schumann resonance tracking
4. GNSS TEC mapping
5. Magnetometer chains

**Data is available. The tools exist. Independent verification is possible.**

---

*Report generated: April 7, 2026*
*Sources: Public domain ionospheric monitoring networks*
