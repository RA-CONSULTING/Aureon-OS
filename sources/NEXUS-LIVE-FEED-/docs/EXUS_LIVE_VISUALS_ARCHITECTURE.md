# EXUS Live Visuals Architecture

## From Sensor to Screen: Visual Data Pipeline

| Stage | Description |
| --- | --- |
| 1 | Sensor captures raw data |
| 2 | Data transmitted to Nexus Core |
| 3 | AI processes and analyzes data |
| 4 | Visualization engine renders graphics |
| 5 | Display systems show live visuals |
| 6 | User interacts with visuals |

---

## Part 1: Sensor Recording Systems

### 1. Electromagnetic Spectrum Sensors

**Data Capture**

- Schumann resonances (7.83 Hz, 14.3 Hz, 20.8 Hz)
- ELF/VLF waves (3 Hz – 30 kHz)
- Magnetic field strength and direction
- Electric field fluctuations

**Hardware**

- **Sensor:** Induction coil magnetometer + electric field antenna
- **ADC:** 24-bit analog-to-digital converter, 192 kHz sampling rate
- **Storage:** Local buffer (1 GB), continuous recording
- **Transmission:** 4G/5G or Ethernet, 1 Mbps upload

**Data Format**

- Raw: Time-series waveform (CSV or binary)
- Processed: FFT spectrum (JSON), 1-second intervals
- Metadata: GPS coordinates, timestamp, sensor ID, temperature

### 2. Atmospheric Sensors

**Data Capture**

- Air quality (PM2.5, PM10, CO₂, NO₂, O₃)
- Temperature, humidity, pressure
- Wind speed and direction
- UV index

**Hardware**

- **Sensor:** Multi-gas sensor array (e.g., Sensirion SPS30, BME680)
- **Processor:** Raspberry Pi 4 or Arduino Mega
- **Storage:** MicroSD card (32 GB), hourly logs
- **Transmission:** WiFi or 4G, 100 kbps upload

**Data Format**

- JSON object every 60 seconds
- Fields: `timestamp`, `location`, `PM25`, `CO2`, `temp`, `humidity`, `pressure`, `UV`

### 3. Seismic Sensors

**Data Capture**

- Ground vibrations (0.1 Hz – 100 Hz)
- Microseismic activity
- Earth resonance patterns

**Hardware**

- **Sensor:** Geophone or accelerometer (e.g., TC-1 seismometer)
- **ADC:** 24-bit, 200 Hz sampling rate
- **Storage:** Local SSD (500 GB), continuous recording
- **Transmission:** Ethernet, 500 kbps upload

**Data Format**

- MiniSEED format (standard seismic data)
- Converted to JSON for web display

### 4. Biometric Sensors (Human Coherence)

**Data Capture**

- Heart rate variability (HRV)
- Heart coherence score
- Breathing rate
- Skin conductance (optional)

**Hardware & Flow**

- **Sensor:** HeartMath Inner Balance sensor or Polar H10 chest strap
- **Connection:** Bluetooth Low Energy (BLE) to smartphone
- **App:** NEXUS app records via phone camera (PPG) or external sensor
- **Transmission:** Real-time to Nexus Core via app

**Data Format**

- JSON: `timestamp`, `user_id` (anonymous), `HRV`, `coherence_score`, `breathing_rate`
- Aggregated: Global average HRV every 5 minutes

### 5. Space Weather Sensors

**Data Capture**

- Solar wind speed and density
- Geomagnetic field (Kp index)
- Cosmic ray flux
- Solar X-ray flux

**Hardware & Flow**

- **Source:** NOAA SWPC API (public data)
- **Polling:** Every 5 minutes via HTTP request
- **Storage:** PostgreSQL database at Nexus Core

**Data Format**

- JSON from NOAA API
- Fields: `timestamp`, `solar_wind_speed`, `Kp_index`, `X_ray_flux`

### 6. Visual Cameras (Sacred Sites)

**Data Capture**

- Time-lapse photography (sunrise, sunset, celestial events)
- Live video streams (optional)
- Sky conditions (clouds, aurora, meteors)

**Hardware**

- **Camera:** Raspberry Pi HQ Camera or GoPro
- **Storage:** Local SD card (128 GB), 1 photo every 10 minutes
- **Transmission:** Upload to cloud storage (AWS S3), daily batch

**Data Format**

- JPEG images with EXIF metadata (timestamp, GPS, camera settings)
- Video: H.264 MP4, 1080p, 30 fps

---

## Part 2: Data Transmission to Nexus Core

### Transmission Summary

| Sensor Type | Method | Bandwidth | Latency |
| --- | --- | --- | --- |
| EM spectrum | 4G/5G or Ethernet | 1 Mbps | 1–2 s |
| Atmospheric | WiFi or 4G | 100 kbps | 5–10 s |
| Seismic | Ethernet | 500 kbps | ~1 s |
| Biometric | App → Cloud (HTTPS) | 10 kbps | Real-time |
| Space weather | API polling | 1 kbps | 5 min |
| Visual | WiFi → Cloud storage | Variable | Daily batch |

### Pipeline Architecture

1. **Sensor → Edge Device (Local Processing)**
   - Raspberry Pi or Arduino runs edge AI
   - Filters noise, compresses data, detects anomalies
   - Reduces bandwidth by 80–90%
2. **Edge Device → Nexus Core (Cloud Server)**
   - MQTT for IoT devices (lightweight, reliable)
   - HTTPS for app-based data (secure)
   - WebSocket for real-time streaming
3. **Nexus Core → Database (Storage)**
   - PostgreSQL for structured data (sensor readings, metadata)
   - InfluxDB for time-series data (high-speed writes)
   - AWS S3 for images and videos

---

## Part 3: AI Processing & Analysis

### Real-Time Pipeline

1. **Data Ingestion**
   - Apache Kafka ingests and tags streams by sensor type and location
2. **Anomaly Detection**
   - LSTM neural networks identify unusual patterns
   - Threshold alerts trigger notifications
3. **Pattern Recognition**
   - Cross-correlation analysis surfaces relationships (e.g., Schumann spikes correlated with HRV changes)
4. **Predictive Modeling**
   - Forecasts the next 24–48 hours using historical baselines
   - Example: Predict geomagnetic storm impact on coherence metrics
5. **Insight Generation**
   - Natural language generation (GPT-4) produces human-readable summaries
   - Example: "Schumann resonance peaked at 8.2 Hz today, 15% above baseline. Users reported increased clarity."

---

## Part 4: Visualization Engine

### Rendering Technologies

| Visual Type | Technology | Libraries/Tools |
| --- | --- | --- |
| 2D line graphs | JavaScript | Chart.js, D3.js |
| Heat maps | JavaScript | Leaflet.js + Heatmap.js |
| 3D globe | WebGL | Three.js + Cesium.js |
| Sacred geometry | Canvas API | Custom GLSL shaders |
| Spectrograms | JavaScript | Plotly.js |
| Network graphs | JavaScript | Cytoscape.js |
| Real-time waveforms | WebGL | Smoothie Charts |

### Rendering Pipeline

1. **Data Query** – Client requests data from Nexus Core API (e.g., last 24 hours of Schumann resonance).
2. **Data Transformation** – Backend converts records to JSON arrays and down-samples for performance (e.g., one point per minute).
3. **Client-Side Rendering** – JavaScript libraries render visuals; WebGL ensures smooth 60 fps animation.
4. **User Interaction** – Touch/mouse events enable zoom, pan, filtering; new queries fetch detailed data on demand.

---

## Part 5: Display Systems

### 1. Mobile App (iOS/Android)

- OLED or LCD displays, 60–120 Hz; 1080p–4K resolutions
- Adaptive resolution and dark mode optimizations
- Haptic feedback for key interactions
- Visuals: circular coherence gauge, zoomable line graphs, heat-map overlays, sacred geometry breathing animations

### 2. Web App (Desktop/Laptop)

- LCD/OLED monitors, 60–144 Hz; 1080p–4K
- Larger canvases for multi-panel dashboards
- Mouse hover tooltips and keyboard shortcuts
- Visuals: multi-sensor dashboards, full-screen 3D globe, spectrogram waterfalls, sensor network graphs

### 3. Public Displays (Queen's University)

- 55" 4K LCD displays driven by Raspberry Pi 4 (8 GB RAM)
- Kiosk mode browser with 60-second auto-refresh
- QR code overlay promotes mobile app download
- Visuals: planetary coherence hero gauge, scrolling sensor ticker, campus map, rotating AI-generated insights

### 4. Immersive Displays (Future VR/AR)

- Hardware: Meta Quest 3, Apple Vision Pro, smartphone AR (ARKit/ARCore)
- Visuals: 3D data clouds, immersive sacred geometry, AR overlays anchored to sacred sites

---

## Part 6: Signature Live Visuals

### Planetary Coherence Gauge

- **Source:** Aggregated EM, atmospheric, biometric, and seismic data
- **Update Rate:** Every 5 seconds via weighted algorithm
- **Display:** Circular SVG animation with sacred geometry, red → violet gradient, pulsing to Schumann resonance
- **Interaction:** Tap to expand, long-press to share snapshot

### Schumann Resonance Spectrogram

- **Source:** Induction coil sensor with 1-second FFTs stored in InfluxDB
- **Display:** Waterfall plot (time vs. frequency) with amplitude-coded color intensity (Plotly.js)
- **Interaction:** Pinch-zoom frequency bands, tap to read precise values

### Global Sensor Network Map

- **Source:** Sensor metadata with 60-second status pings
- **Display:** 3D globe via Three.js + Cesium.js, color-coded pins, animated data flows
- **Interaction:** Rotate globe, tap pins for detail cards, filter by sensor type/status

### Heart Coherence Wave

- **Source:** Anonymous global HRV averages updated every 5 minutes
- **Display:** Smooth sine-wave animation with amplitude representing coherence and color shifts by frequency
- **Interaction:** Tap to contribute HRV data, long-press for meditation timer

### Sacred Geometry Mandala

- **Source:** Schumann frequency (rotation), global coherence (symmetry), solar wind speed (color shifts)
- **Display:** Canvas + GLSL fractal (Flower of Life base) at 60 fps
- **Interaction:** Pinch to zoom, rotate device to spin via gyroscope, shake to randomize pattern

---

**The eyes of the Nexus are open—sensor to screen, data to display, recording to rendering.**
