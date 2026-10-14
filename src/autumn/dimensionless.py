"""Nondimensional numbers and trajectory regime classification for falling plates.

References:
    Andersen, A., Pesavento, U., & Wang, Z. J. (2005a).
    Unsteady aerodynamics of fluttering and tumbling plates.
    Journal of Fluid Mechanics, 541, 65-90. DOI: 10.1017/S002211200500594X.

    Andersen, A., Pesavento, U., & Wang, Z. J. (2005b).
    Analysis of transitions between fluttering, tumbling and steady descent of falling cards.
    Journal of Fluid Mechanics, 541, 91-104. DOI: 10.1017/S0022112005005847.
"""

from __future__ import annotations

import math
from typing import Dict, Sequence, Tuple
import numpy as np

from autumn.params import RegimeClassifierParams


def compute_i_star(rho_s: float, h: float, rho_f: float, L: float) -> float:
    r"""Compute dimensionless moment of inertia I* for a 2D plate.

    Equation:
        I^* = \frac{\rho_s h}{\rho_f L}

    Note:
        Do NOT use I/(m R^2): it is constant for a solid ellipse/disk and carries no information.
    """
    if rho_f <= 0 or L <= 0:
        raise ValueError("rho_f and L must be strictly positive.")
    return (rho_s * h) / (rho_f * L)


def compute_froude_velocity_scale(rho_s: float, rho_f: float, g: float, h: float) -> float:
    r"""Compute velocity scale (Froude-type velocity scale).

    Equation:
        U_t = \sqrt{\left(\frac{\rho_s}{\rho_f} - 1\right) g h}
    """
    buoyant_ratio = (rho_s / rho_f) - 1.0
    if buoyant_ratio <= 0:
        return 0.0
    return math.sqrt(buoyant_ratio * g * h)


def compute_reynolds_number(rho_f: float, U: float, L: float, mu: float) -> float:
    r"""Compute Reynolds number based on plate chord and mean descent speed U.

    Equation:
        \mathrm{Re} = \frac{\rho_f U L}{\mu}
    """
    if mu <= 0:
        raise ValueError("Viscosity mu must be strictly positive.")
    return (rho_f * abs(U) * L) / mu


def compute_strouhal_number(f: float, L: float, U: float) -> float:
    r"""Compute Strouhal number from dominant oscillation frequency f.

    Equation:
        \mathrm{St} = \frac{f L}{U}
    """
    if abs(U) < 1e-9:
        return 0.0
    return (f * L) / abs(U)


def classify_regime(
    t: np.ndarray,
    Y: np.ndarray,
    theta: np.ndarray,
    omega: np.ndarray,
    H_fall: float,
    params: RegimeClassifierParams
) -> Tuple[str, Dict[str, float]]:
    r"""Classify falling regime into 'steady', 'fluttering', 'tumbling', or 'mixed'.

    Rules (discarding initial transient t < max(0.20*t_end, 1.0 s) or Y <= Y0 - 0.20*H_fall):
        1. steady: std(theta_post) < 1.0 deg (or ptp < 2.0 deg) and zero full revolutions.
        2. fluttering: bounded periodic oscillation (ptp < 360 deg, no full 2*pi flips) with std(theta_post) >= 1.0 deg.
        3. tumbling: continuous unidirectional autorotation: total net rotation >= 2 * 360 deg
           AND plate does not complete a full 180 deg rotation in the opposite direction after establishing spin.
        4. mixed (or chaotic_tumble): trajectories that complete at least one full 360 deg flip
           AND exhibit direction reversals (angular excursion exceeding 90 deg in the opposite direction).

    Args:
        t: Time array [s]
        Y: Vertical position array [m] (decreasing downward)
        theta: Continuous orientation angle array [rad]
        omega: Angular velocity array [rad/s]
        H_fall: Total target fall depth [m]
        params: Classification threshold parameters

    Returns:
        regime: One of ('steady', 'fluttering', 'tumbling', 'mixed')
        metrics: Dictionary of diagnostic properties
    """
    t_end = float(t[-1])
    t_transient = max(params.transient_fraction * t_end, params.transient_t_min)
    y0 = float(Y[0])
    transient_depth = params.transient_fraction * H_fall
    valid_mask = (t >= t_transient) & (Y <= (y0 - transient_depth))

    if np.sum(valid_mask) < 10:
        valid_mask = t >= (0.5 * t_end)
        if np.sum(valid_mask) < 5:
            valid_mask = np.ones_like(t, dtype=bool)

    th_crop = theta[valid_mask]
    om_crop = omega[valid_mask]

    ptp_theta = float(np.ptp(th_crop))
    std_theta = float(np.std(th_crop))

    # Net rotation across post-transient signal
    delta_th_net = float(th_crop[-1] - th_crop[0])
    net_rotation = abs(delta_th_net)
    n_flips = int(net_rotation // (2.0 * math.pi))

    # Calculate maximum directional reversal (backward excursion relative to dominant spin)
    if delta_th_net >= 0:
        running_max = np.maximum.accumulate(th_crop)
        max_backward_excursion = float(np.max(running_max - th_crop))
    else:
        running_min = np.minimum.accumulate(th_crop)
        max_backward_excursion = float(np.max(th_crop - running_min))

    std_deg = math.degrees(std_theta)
    ptp_deg = math.degrees(ptp_theta)
    back_deg = math.degrees(max_backward_excursion)

    metrics = {
        "theta_range_rad": ptp_theta,
        "theta_range_deg": ptp_deg,
        "std_theta_deg": std_deg,
        "n_flips": float(n_flips),
        "delta_theta_net_rad": delta_th_net,
        "max_backward_excursion_deg": back_deg
    }

    # 1. Steady: post-transient standard deviation < 1 deg (or ptp < 2 deg) and no flips
    if (std_deg < params.theta_std_steady_deg or ptp_deg < params.theta_ptp_steady_deg) and ptp_deg < 360.0:
        return "steady", metrics

    # 2. Tumbling: at least 2 full rotations with no sustained reversal (> 180 deg) in opposite direction
    if (net_rotation >= params.min_flips_tumble * 2.0 * math.pi) and (back_deg < params.max_reversal_tumble_deg):
        return "tumbling", metrics

    # 3. Fluttering: bounded periodic oscillations without completing any full 360 deg flip
    if ptp_deg < 360.0:
        return "fluttering", metrics

    # 4. Mixed / Chaotic tumbling
    return "mixed", metrics
