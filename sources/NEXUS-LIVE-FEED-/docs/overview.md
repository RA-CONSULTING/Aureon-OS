# VR/AR Light Manipulation Pipeline: Overview

## 1. Vision

This project is a conceptual simulator for next-generation VR/AR display technologies. It provides a modular, end-to-end Python pipeline to model, simulate, and visualize the journey of light from a display source to the human eye.

The goal is to bridge the gap between theoretical optics and practical implementation, enabling rapid prototyping and exploration of complex display systems.

## 2. Core Components

The pipeline is composed of three primary modules:

*   **`optics/`**: Simulates the fundamental optical components that guide and shape light.
    *   **Waveguide:** Models Total Internal Reflection (TIR) in a planar waveguide.
    *   **Diffractive Optical Element (DOE):** Simulates how a DOE redirects light at a specific angle.
    *   **Varifocal Lens:** Models a lens with an electronically tunable focal length to adjust for virtual object depth.
    *   **Spatial Light Modulator (SLM):** Generates phase patterns for computer-generated holography.
    *   **Fresnel Propagation:** Simulates the propagation of a light field to reconstruct a holographic image in space.

*   **`rendering/`**: Focuses on image generation and processing techniques that mimic human vision.
    *   **Foveated Rendering:** Implements a rendering technique that saves computational resources by rendering the user's gaze point at high resolution and the periphery at low resolution.
    *   **Synthetic Scene:** Creates a simple, dynamic scene to test rendering and eye-tracking.

*   **`projection/`**: Produces tangible outputs for real-world display and demonstration.
    *   **Projector-Ready Replay:** Generates an intensity-only video of a holographic replay, suitable for playback on a standard projector to create a 3D visual effect.

## 3. The Flow of Light

The pipeline follows a logical flow:

1.  **Generation:** A synthetic scene is created (`rendering`).
2.  **Perception-Aware Processing:** The scene is processed with foveated rendering, mimicking how the eye perceives detail (`rendering`).
3.  **Holographic Encoding:** A target image is encoded into a phase-only hologram via an SLM (`optics`).
4.  **Propagation & Reconstruction:** The hologram is numerically propagated using the Fresnel approximation to reconstruct a 3D image at various depths (`optics`).
5.  **Output:** The final holographic replay is saved as a video, ready for projection (`projection`).

This modular structure allows for each component to be studied and modified independently, creating a powerful toolkit for research and education in display technologies.
