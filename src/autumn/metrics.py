"""Trajectory metrics, FFT frequency analysis, and energy accounting for falling plates.

Reference:
    Andersen, A., Pesavento, U., & Wang, Z. J. (2005).
    Unsteady aerodynamics of fluttering and tumbling plates.
    Journal of Fluid Mechanics, 541, 65-90.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple
import numpy as np
from scipy.integrate import cumulative_trapezoid

from autumn.dimensionless import (
    classify_regime,
    compute_froude_velocity_scale,
    compute_reynolds_number,
    compute_strouhal_number,
)
from autumn.forces import compute_viscous_forces_and_torque
from autumn.model import AutumnModel
from autumn.params import RegimeClassifierParams


def compute_fft_frequency(
    t: np.ndarray,
    theta: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, float]:
    r"""Compute dominant oscillation frequency of orientation theta(t) using FFT.

    Args:
        t: Uniformly spaced time array [s].
        theta: Orientation angle array [rad].

    Returns:
        freqs: Frequency array [Hz].
        psd: Power spectral density.
        f_dominant: Dominant peak frequency [Hz].
    """
    n = len(t)
    if n < 16:
        return np.array([0.0]), np.array([0.0]), 0.0

    dt = float(np.mean(np.diff(t)))
    # Detrend by subtracting linear drift / mean
    theta_detrend = theta - np.polyval(np.polyfit(t, theta, 1), t)

    # Apply Hanning window
    window = np.hanning(n)
    fft_vals = np.fft.rfft(theta_detrend * window)
    freqs = np.fft.rfftfreq(n, d=dt)
    psd = (np.abs(fft_vals) ** 2) / n

    # Ignore near-DC frequencies (below 0.1 Hz)
    valid_idx = freqs >= 0.1
    if np.any(valid_idx) and np.max(psd[valid_idx]) > 1e-12:
        dominant_idx = np.argmax(psd[valid_idx])
        f_dominant = float(freqs[valid_idx][dominant_idx])
    else:
        f_dominant = 0.0

    return freqs, psd, f_dominant


def compute_energy_budget(
    res
) -> Dict[str, np.ndarray | float]:
    r"""Compute time series of kinetic, potential, dissipated, and total energy.

    Equations:
        T(t) = \frac{1}{2}(m + m_{11})u^2 + \frac{1}{2}(m + m_{22})v^2 + \frac{1}{2}(I + I_a)\omega^2
        V_{\mathrm{pot}}(t) = (m - m_f) g Y(t)
        P_{\mathrm{diss}}(t) = u F_u + v F_v + \omega \tau
        W_{\mathrm{diss}}(t) = \int_0^t P_{\mathrm{diss}}(t') dt'
        E_{\mathrm{total}}(t) = T(t) + V_{\mathrm{pot}}(t) + W_{\mathrm{diss}}(t)

    Normalization (per user amendment):
        \Delta E_{\mathrm{pot}} = (m - m_f) g H_{\mathrm{fall}}
        \text{residual} = \frac{|E_{\mathrm{total}}(t) - E_{\mathrm{total}}(0)|}{\Delta E_{\mathrm{pot}}}

    Returns:
        Dict containing energy arrays and max closure error percentage.
    """
    model = AutumnModel(plate=res.plate, fluid=res.fluid, coeffs=res.coeffs)

    n = len(res.t)
    e_kin = np.zeros(n)
    e_pot = np.zeros(n)
    p_diss = np.zeros(n)

    for i in range(n):
        st = [res.X[i], res.Y[i], res.theta[i], res.u[i], res.v[i], res.omega[i]]
        e_kin[i] = model.kinetic_energy(st)
        e_pot[i] = model.potential_energy(st)

        f_u, f_v, tau = compute_viscous_forces_and_torque(
            res.u[i], res.v[i], res.omega[i], res.plate.L, res.fluid.rho_f, res.coeffs
        )
        p_diss[i] = res.u[i] * f_u + res.v[i] * f_v + res.omega[i] * tau

    w_diss = cumulative_trapezoid(p_diss, res.t, initial=0.0)
    e_total = e_kin + e_pot + w_diss

    delta_e_pot_drop = (res.plate.mass - res.plate.mass_fluid(res.fluid.rho_f)) * res.fluid.g * res.H_fall
    norm_factor = max(abs(delta_e_pot_drop), 1e-9)

    residual_pct = np.abs(e_total - e_total[0]) / norm_factor * 100.0
    max_residual_pct = float(np.max(residual_pct))

    return {
        "t": res.t,
        "E_kin": e_kin,
        "E_pot": e_pot,
        "W_diss": w_diss,
        "E_total": e_total,
        "delta_e_pot_drop": delta_e_pot_drop,
        "residual_pct": residual_pct,
        "max_residual_pct": max_residual_pct
    }


def compute_trajectory_summary(
    res,
    classifier_params: RegimeClassifierParams
) -> Dict[str, object]:
    r"""Compute complete diagnostic summary for a single trajectory."""
    regime, reg_metrics = classify_regime(
        t=res.t,
        Y=res.Y,
        theta=res.theta,
        omega=res.omega,
        H_fall=res.H_fall,
        params=classifier_params
    )

    # Discard transient for descent velocity calculation
    y0 = res.Y[0]
    transient_depth = classifier_params.transient_fraction * res.H_fall
    valid_mask = res.Y <= (y0 - transient_depth)
    if np.sum(valid_mask) < 5:
        valid_mask = np.ones_like(res.Y, dtype=bool)

    mean_vy = float(np.mean(np.abs(res.v_Y[valid_mask])))
    mean_speed = float(np.mean(res.speed[valid_mask]))
    lateral_drift = float(abs(res.X[-1] - res.X[0]))

    i_star = res.plate.I_star(res.fluid.rho_f)
    re = compute_reynolds_number(res.fluid.rho_f, mean_speed, res.plate.L, res.fluid.mu)
    u_t = compute_froude_velocity_scale(res.plate.rho_s, res.fluid.rho_f, res.fluid.g, res.plate.h)

    freqs, psd, f_dom = compute_fft_frequency(res.t[valid_mask], res.theta[valid_mask])
    st = compute_strouhal_number(f_dom, res.plate.L, mean_speed)

    return {
        "plate_name": res.plate.name,
        "I_star": i_star,
        "Re": re,
        "U_mean": mean_speed,
        "U_t": u_t,
        "f_dom": f_dom,
        "St": st,
        "regime": regime,
        "lateral_drift": lateral_drift,
        "reached_bottom": res.reached_bottom,
        "timed_out": res.timed_out,
        "classifier_metrics": reg_metrics,
        "freqs": freqs,
        "psd": psd
    }
