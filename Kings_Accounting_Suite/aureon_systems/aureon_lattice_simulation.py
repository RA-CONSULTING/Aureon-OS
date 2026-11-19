"""Lattice field sketch kept beside the Kings suite.

Importing this module does not invent a field, draw noise, or write a figure.
There is no measured lattice series here. Calling the generator says no data.
The file stays in the tree until Gary decides whether the duplicate itself goes.
"""

from aureon_baton_link import link_system as _baton_link

_baton_link(__name__)

# Frequency labels only. No samples are synthesised from them.
F_DISTORTION = 440.0  # Mars Frequency (Fear/Extraction)
F_KEY = 198.4  # Belfast Frequency ("Ahhhhh Bannnnn")
F_SOLVENT = 528.0  # Love Frequency ("Green Proper Borax")

NO_DATA = (
    "no data: lattice simulation has no measured field; "
    "random noise is not a reading and no figure is written"
)


def generate_phase(phase_name, distortion_amp, key_amp, solvent_amp, noise_level):
    """Refuse a synthetic lattice. A measured series has to be passed in later."""

    del phase_name, distortion_amp, key_amp, solvent_amp, noise_level
    raise RuntimeError(NO_DATA)


def main() -> None:
    raise SystemExit(NO_DATA)


if __name__ == "__main__":
    main()
