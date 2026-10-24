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
    r"""Compute Froude velocity scale based on full plate thickness h.

    Equation:
        U_t = \sqrt{\left(\frac{\rho_s}{\rho_f} - 1\right) g h}
    """
    buoyant_ratio = (rho_s / rho_f) - 1.0
    if buoyant_ratio <= 0:
        return 0.0
    return math.sqrt(buoyant_ratio * g * h)


def compute_andersen_velocity_scale(rho_s: float, rho_f: float, g: float, b: float) -> float:
    r"""Compute characteristic velocity scale U_0 from Andersen et al. (2005b) eq. (2.3) based on semi-minor axis b = h / 2.

    Equation:
        U_0 = \sqrt{\left(\frac{\rho_s}{\rho_f} - 1\right) g b} = \sqrt{\left(\frac{\rho_s}{\rho_f} - 1\right) g \frac{h}{2}} = \frac{U_t}{\sqrt{2}}
    """
    buoyant_ratio = (rho_s / rho_f) - 1.0
    if buoyant_ratio <= 0:
        return 0.0
    return math.sqrt(buoyant_ratio * g * b)


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
    params: RegimeClassifierParams,
    tau_0: Optional[float] = None
) -> Tuple[str, Dict[str, float]]:
    r"""Classify falling regime into 'steady', 'fluttering', 'tumbling', 'mixed', or 'undetermined'.

    Rules (discarding initial transient t < max(20*tau_0, 0.20*t_end) or Y <= Y0 - 0.20*H_fall):
        1. undetermined: post-transient window duration < min_window_time_units * tau_0,
           OR oscillation cycles < min_cycles,
           OR relative difference between middle third and last third amplitude > stationarity_tolerance (15%).
        2. steady: std(theta_post) < 1.0 deg (or ptp < 2.0 deg) across window and both middle/last thirds.
        3. tumbling: continuous unidirectional autorotation: total net rotation >= 2 * 360 deg
           AND plate does not complete a full 180 deg rotation in the opposite direction after establishing spin.
        4. fluttering: bounded periodic oscillation (ptp < 300 deg, no full 2*pi flips) with std(theta_post) >= 1.0 deg.
        5. mixed (or chaotic_tumble): trajectories that complete at least one full 360 deg flip
           AND exhibit direction reversals (angular excursion exceeding 90 deg in the opposite direction).

    Args:
        t: Time array [s]
        Y: Vertical position array [m] (decreasing downward)
        theta: Continuous orientation angle array [rad]
        omega: Angular velocity array [rad/s]
        H_fall: Total target fall depth [m]
        params: Classification threshold parameters
        tau_0: Characteristic timescale a / U_0 [s] (optional, defaults to 0.05 s)

    Returns:
        regime: One of ('steady', 'fluttering', 'tumbling', 'mixed', 'undetermined')
        metrics: Dictionary of diagnostic properties
    """
    t_end = float(t[-1])
    effective_tau0 = float(tau_0) if (tau_0 is not None and tau_0 > 0.0) else 0.05
    transient_time_thresh = getattr(params, "transient_time_units", 20.0) * effective_tau0 if (tau_0 is not None and tau_0 > 0.0) else params.transient_t_min
    t_transient = max(params.transient_fraction * t_end, transient_time_thresh)
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

    mean_abs_om = float(np.mean(np.abs(om_crop)))
    mean_om = float(np.mean(om_crop))
    std_om = float(np.std(om_crop))
    spin_ratio = float(abs(mean_om) / (mean_abs_om + 1e-9))
    rel_std_om = float(std_om / (mean_abs_om + 1e-9))

    std_deg = math.degrees(std_theta)
    ptp_deg = math.degrees(ptp_theta)
    back_deg = math.degrees(max_backward_excursion)

    dt_window = float(t[valid_mask][-1] - t[valid_mask][0]) if np.sum(valid_mask) > 1 else 0.0
    window_time_units = dt_window / effective_tau0

    # Count oscillation cycles
    zc = int(np.sum((om_crop[:-1] * om_crop[1:]) < 0))
    net_turns = net_rotation / (2.0 * math.pi)
    n_cycles = float(max(net_turns, zc / 2.0))

    metrics = {
        "theta_range_rad": ptp_theta,
        "theta_range_deg": ptp_deg,
        "std_theta_deg": std_deg,
        "n_flips": float(n_flips),
        "delta_theta_net_rad": delta_th_net,
        "max_backward_excursion_deg": back_deg,
        "spin_ratio": spin_ratio,
        "rel_std_omega": rel_std_om,
        "mean_abs_omega": mean_abs_om,
        "window_duration_s": dt_window,
        "window_time_units": window_time_units,
        "n_cycles": n_cycles,
        "stationarity_err": 0.0,
    }

    # 1. Steady check: if post-transient standard deviation < 1 deg (or ptp < 2 deg) and no flips
    if (std_deg < params.theta_std_steady_deg or ptp_deg < params.theta_ptp_steady_deg) and ptp_deg < 360.0:
        n3 = len(th_crop) // 3
        if n3 >= 2:
            th2, th3 = th_crop[n3:2*n3], th_crop[2*n3:]
            ptp2_deg = math.degrees(float(np.ptp(th2)))
            ptp3_deg = math.degrees(float(np.ptp(th3)))
            if ptp2_deg < params.theta_ptp_steady_deg and ptp3_deg < params.theta_ptp_steady_deg:
                return "steady", metrics
        else:
            return "steady", metrics

    # 2. Horizon duration check: require at least min_window_time_units
    min_window_tu = getattr(params, "min_window_time_units", 30.0)
    if window_time_units < min_window_tu and len(t) > 5:
        metrics["rejection_reason"] = "window_too_short"
        return "undetermined", metrics

    # 3. Minimum oscillation cycles check
    min_cycles = getattr(params, "min_cycles", 2.0)
    if n_cycles < min_cycles and len(t) > 5:
        metrics["rejection_reason"] = "insufficient_cycles"
        return "undetermined", metrics

    # 4. Stationarity check: middle third vs last third amplitude within stationarity_tolerance (15%)
    n3 = len(th_crop) // 3
    if n3 >= 2:
        th2, th3 = th_crop[n3:2*n3], th_crop[2*n3:]
        om2, om3 = om_crop[n3:2*n3], om_crop[2*n3:]
        if ptp_deg < params.theta_ptp_flutter_max_deg and net_rotation < 2.0 * math.pi:
            amp2 = float(np.ptp(th2))
            amp3 = float(np.ptp(th3))
        else:
            amp2 = float(np.ptp(om2))
            amp3 = float(np.ptp(om3))

        stationarity_err = abs(amp3 - amp2) / max(amp2, 1e-6)
        metrics["stationarity_err"] = stationarity_err
        stationarity_tol = getattr(params, "stationarity_tolerance", 0.15)
        if stationarity_err > stationarity_tol:
            metrics["rejection_reason"] = "non_stationary_amplitude"
            return "undetermined", metrics

    # 5. Tumbling: at least min_flips_tumble full rotations with predominant unidirectional spin
    if (net_rotation >= params.min_flips_tumble * 2.0 * math.pi) and (
        back_deg < params.max_reversal_tumble_deg or spin_ratio >= params.min_spin_ratio_tumble
    ):
        return "tumbling", metrics

    # 6. Fluttering: bounded periodic oscillations below separatrix threshold (ptp < theta_ptp_flutter_max_deg)
    # with no full rotations and low spin ratio (oscillating back and forth about zero)
    if (ptp_deg < params.theta_ptp_flutter_max_deg) and (net_rotation < 2.0 * math.pi) and (spin_ratio < params.min_spin_ratio_tumble):
        return "fluttering", metrics

    # 7. Mixed / Chaotic: anything else (separatrix swings, erratic non-uniform autorotation)
    return "mixed", metrics
