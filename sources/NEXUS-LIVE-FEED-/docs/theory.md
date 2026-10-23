# VR/AR Pipeline: Theoretical Concepts

This document provides a brief theoretical background for the key concepts simulated in this pipeline.

## 1. Waveguides and Total Internal Reflection (TIR)

*   **Concept:** A waveguide is a structure that guides waves, such as light, with minimal loss of energy. In optical systems, this is often achieved using a transparent material with a high refractive index (`n_core`) surrounded by a material with a lower refractive index (`n_clad`).
*   **Mechanism:** Light traveling from a denser medium to a less dense one is bent away from the normal. If the angle of incidence is greater than a specific **critical angle**, the light is not refracted at all but is instead completely reflected back into the denser medium. This phenomenon is called **Total Internal Reflection (TIR)**.
*   **Simulation:** Our `WaveguideSimulator` calculates this critical angle based on the refractive indices and determines if an incoming light ray will be guided via TIR or leak out.

## 2. Foveated Rendering

*   **Concept:** The human eye does not see the world in uniform detail. Our central vision (the fovea) perceives high resolution, while our peripheral vision perceives low resolution. Foveated rendering is a computer graphics technique that mimics this behavior.
*   **Mechanism:** By tracking the user's gaze, a system can render the exact spot the user is looking at in high quality, while rendering the surrounding areas at a much lower quality. This dramatically reduces the computational load without a noticeable loss in perceived visual quality.
*   **Simulation:** The `FoveatedRenderer` creates a mask centered on a simulated "gaze point." The area inside the mask is kept at high resolution, while the area outside is blurred. The two are then blended to create the final image.

## 3. Computer-Generated Holography (CGH)

*   **Concept:** Holography is a technique that records and reconstructs a light field, preserving its 3D structure (both amplitude and phase). Computer-Generated Holography (CGH) uses a computer to calculate the interference pattern (the hologram) that will produce a desired 3D image when illuminated.
*   **Mechanism:**
    1.  A **Spatial Light Modulator (SLM)** is used as a dynamic, high-resolution screen that can manipulate the phase of light on a pixel-by-pixel basis.
    2.  A computer calculates the required phase pattern. A common method is to perform a Fourier transform of the target 2D image to find the phase distribution in the frequency domain.
    3.  This phase pattern is displayed on the SLM. When a coherent light source (like a laser) illuminates the SLM, the light is modulated. This modulated light, when it propagates through space, reconstructs the intended 3D object.

## 4. Fresnel Propagation

*   **Concept:** To simulate the reconstruction of a hologram, we must model how the light field propagates through space after being modulated by the SLM.
*   **Mechanism:** The **Fresnel diffraction integral** is a mathematical approximation used to calculate the light field at a certain distance `z` from an initial field. It is computationally efficient to solve this using Fourier transforms. The process involves:
    1.  Taking the Fourier transform of the initial light field (from the SLM).
    2.  Multiplying it by a "transfer function" (also called the Fresnel kernel) that depends on the propagation distance `z`.
    3.  Taking the inverse Fourier transform of the result to get the complex light field at distance `z`.
*   **Simulation:** The `fresnel_propagate` function implements this process. By simulating propagation at various distances `z`, we can generate a video that shows the holographic image coming into focus, just as it would in a real optical setup.
