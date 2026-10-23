# VR/AR Pipeline: Usage Guide

## 1. Installation

This project is designed as a standard Python package. To install it and its dependencies, follow these steps.

### Prerequisites

*   Python 3.8 or higher
*   `pip` (Python package installer)

### Steps

1.  **Clone the Repository:**

    ```bash
    git clone <your-repository-url>
    cd vrar_pipeline
    ```

2.  **Install in Editable Mode:**

    We recommend installing the package in "editable" mode (`-e`). This allows you to modify the source code and see the changes immediately without reinstalling.

    ```bash
    pip install -e .
    ```

    This command reads the `setup.py` and `requirements.txt` files to install the necessary libraries (`numpy`, `scipy`, `matplotlib`) and creates an entry point for our main demo.

## 2. Running the Demos

The primary entry point is the `vrar-demo` command, which becomes available after installation.

### Main Demonstration

This command runs the `main.py` script, which executes two key simulations:

1.  **Optical Components Diagnostics:** It prints the state of the Waveguide, DOE, and Varifocal Lens.
2.  **Projector Replay Generation:** It generates the `projector_replay.mp4` video, which shows a holographic image coming into focus.

To run it, simply execute:

```bash
vrar-demo
```

### Expected Output

You will see the following in your terminal:

```
Waveguide state: Guided (TIR)
DOE output angle (deg): <some_value>
Lens focal length (mm): <some_value>
Saved projector video: projector_replay.mp4
```

And a file named `projector_replay.mp4` will be created in your directory.

## 3. Exploring the Modules

Because the project is structured as a library, you can easily import and use individual components in your own Python scripts or an interactive session (like Jupyter or IPython).

**Example: Test the Waveguide Simulator**

```python
from optics.waveguide import WaveguideSimulator
import numpy as np

# Initialize the simulator
wg = WaveguideSimulator()

# Define an input angle
input_angle_degrees = 45
input_angle_radians = np.deg2rad(input_angle_degrees)

# Check the propagation state
state = wg.propagate(input_angle_radians)

print(f"For an input angle of {input_angle_degrees} degrees, the state is: {state}")
print(f"The critical angle for TIR is {np.rad2deg(wg.critical_angle()):.2f} degrees.")
```

This modularity is the core strength of the pipeline, allowing for focused experimentation and expansion.
