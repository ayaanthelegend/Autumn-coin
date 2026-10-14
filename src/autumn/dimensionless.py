"""Nondimensional numbers and trajectory regime classification for falling plates.

Reference:
    Andersen, A., Pesavento, U., & Wang, Z. J. (2005).
    Unsteady aerodynamics of fluttering and tumbling plates.
    Journal of Fluid Mechanics, 541, 65-90.
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

    Rules (Section 4.8 of README & user amendments):
        After discarding the initial transient (first 10% of fall height):
        1. steady: theta_range < theta_range_steady (0.2 rad) AND var(theta) < var_theta_steady
        2. fluttering: n_flips == 0 AND oscillatory motion (theta_range >= 0.2 rad)
        3. tumbling: n_flips >= min_flips_tumble (default 2) with consistent rotation direction
        4. mixed / chaotic: any other trajectory (e.g. fluttering with sporadic flips or direction reversal)

    Args:
        t: Time array [s]
        Y: Vertical position array [m] (decreasing downward)
        theta: Continuous orientation angle array [rad]
        omega: Angular velocity array [rad/s]
        H_fall: Total target fall depth [m]
        params: Classification threshold parameters

    Returns:
        regime: One of ('steady', 'fluttering', 'tumbling', 'mixed')
        metrics: Dictionary of diagnostic properties (theta_range, var_theta, n_flips, sign_consistency)
    """
    # Discard initial transient (first 10% of fall depth: Y > Y0 - 0.1 * H_fall)
    y0 = Y[0]
    transient_depth = params.transient_fraction * H_fall
    valid_mask = Y <= (y0 - transient_depth)

    if np.sum(valid_mask) < 10:
        # If fall didn't reach past transient, use available points
        valid_mask = np.ones_like(Y, dtype=bool)

    th_crop = theta[valid_mask]
    om_crop = omega[valid_mask]

    theta_range = float(np.ptp(th_crop))
    var_theta = float(np.var(th_crop))

    # Net rotations
    delta_th_net = th_crop[-1] - th_crop[0]
    n_flips = int(abs(delta_th_net) // (2.0 * math.pi))

    # Rotation direction consistency: fraction of time spent in dominant omega direction
    pos_omega = np.sum(om_crop > 0)
    neg_omega = np.sum(om_crop < 0)
    total_omega = max(pos_omega + neg_omega, 1)
    dominant_fraction = max(pos_omega, neg_omega) / total_omega

    # Consistent direction means the plate spins mostly in one direction without sustained reversal
    direction_consistent = (dominant_fraction >= 0.85)

    metrics = {
        "theta_range_rad": theta_range,
        "var_theta_rad2": var_theta,
        "n_flips": float(n_flips),
        "dominant_fraction": float(dominant_fraction),
        "delta_theta_net_rad": float(delta_th_net)
    }

    # 1. Steady
    if theta_range < params.theta_range_steady and var_theta < params.var_theta_steady:
        return "steady", metrics

    # 2. Tumbling: at least 2 full flips and consistent rotation direction
    if n_flips >= params.min_flips_tumble and direction_consistent:
        return "tumbling", metrics

    # 3. Fluttering: no full flips (n_flips == 0) and theta oscillates
    if n_flips == 0:
        return "fluttering", metrics

    # 4. Mixed / Chaotic
    return "mixed", metrics
