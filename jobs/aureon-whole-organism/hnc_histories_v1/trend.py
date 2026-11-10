"""Prospectively declared descriptive trend; it is not an asymptotic stability test."""
import numpy as np


def temporal_trend(steps, means):
    x = np.asarray(steps, dtype=float)
    y = np.asarray(means, dtype=float)
    if x.ndim != 1 or y.shape != x.shape:
        raise ValueError('One time series required')
    if len(x) < 8 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or not np.all(np.diff(x) > 0):
        return dict(eligible=False, flag=False)
    centred = x - x.mean()
    slope = float(centred @ (y - y.mean()) / (centred @ centred))
    residual = y - (y.mean() + slope * centred)
    rms = float(np.sqrt(np.mean(residual ** 2)))
    change = abs(slope) * (x[-1] - x[0])
    return dict(eligible=True, slope_per_step=slope, residual_rms=rms, fitted_change=float(change),
                flag=bool(abs(slope) > 1e-8 and change > max(1., 10. * rms)))
