"""Numerical integration engine for Autumn Coin simulations.

Uses scipy.integrate.solve_ivp with DOP853, adaptive t_max, and terminal bottom event.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence
import warnings
import numpy as np
from scipy.integrate import solve_ivp

from autumn.model import AutumnModel
from autumn.params import Coefficients, FluidParams, NumericsParams, PlateParams


@dataclass
class TrajectoryResult:
    """Simulation trajectory output and associated metadata."""
    plate: PlateParams
    fluid: FluidParams
    coeffs: Coefficients
    numerics: NumericsParams
    t: np.ndarray             # Time array [s]
    X: np.ndarray             # Lab X position [m]
    Y: np.ndarray             # Lab Y position [m]
    theta: np.ndarray         # Orientation angle [rad]
    u: np.ndarray             # Body velocity u [m/s]
    v: np.ndarray             # Body velocity v [m/s]
    omega: np.ndarray         # Angular velocity [rad/s]
    v_X: np.ndarray           # Lab velocity X [m/s]
    v_Y: np.ndarray           # Lab velocity Y [m/s]
    speed: np.ndarray         # Speed |V| [m/s]
    reached_bottom: bool      # True if fall depth reached H_fall
    timed_out: bool           # True if run terminated due to t_max before reaching bottom
    H_fall: float             # Target fall depth [m]
    t_max: float              # Cutoff time used [s]

    def to_csv_dict(self) -> dict:
        """Return dict of trajectory arrays for CSV export."""
        return {
            "t": self.t,
            "X": self.X,
            "Y": self.Y,
            "theta": self.theta,
            "u": self.u,
            "v": self.v,
            "omega": self.omega,
            "v_X": self.v_X,
            "v_Y": self.v_Y,
            "speed": self.speed,
            "perturbation_rad": np.full_like(self.t, self.numerics.perturbation_rad)
        }


def simulate_drop(
    plate: PlateParams,
    fluid: FluidParams,
    coeffs: Coefficients,
    numerics: NumericsParams,
    initial_state: Optional[Sequence[float]] = None,
    theta0: float = 0.0,
    u0: float = 0.0,
    v0: float = 0.0,
    omega0: float = 0.0,
    X0: float = 0.0,
    Y0: float = 0.0,
    t_max_override: Optional[float] = None
) -> TrajectoryResult:
    r"""Simulate a single drop of a plate using solve_ivp (DOP853).

    Args:
        plate: Geometric and material parameters of the plate.
        fluid: Fluid environment parameters.
        coeffs: Hydrodynamic force and torque coefficients.
        numerics: Tolerances, time steps, and termination limits.
        initial_state: Optional full 6-element state [X, Y, theta, u, v, omega].
        theta0, u0, v0, omega0, X0, Y0: Used if initial_state is None.
        t_max_override: Optional manual cutoff time.

    Returns:
        TrajectoryResult containing time series and termination flags.
    """
    model = AutumnModel(plate=plate, fluid=fluid, coeffs=coeffs)

    if initial_state is not None:
        y0 = list(initial_state)
    else:
        # Check for exact symmetric drop without perturbation
        if abs(math.sin(theta0)) < 1e-9 and abs(numerics.perturbation_rad) < 1e-12 and u0 == 0.0 and v0 == 0.0 and omega0 == 0.0:
            warnings.warn(
                f"[Autumn Warning] Symmetrically exact vertical drop (theta0={theta0} rad) with zero perturbation: "
                "trajectory direction is determined purely by floating-point roundoff.",
                UserWarning,
                stacklevel=2
            )

        # Controlled symmetry-breaking perturbation to avoid compiler/OS-dependent floating-point roundoff
        theta_init = theta0
        if abs(theta0) < 1e-12 and u0 == 0.0 and v0 == 0.0 and omega0 == 0.0 and numerics.perturbation_rad != 0.0:
            theta_init = numerics.perturbation_rad
        y0 = [X0, Y0, theta_init, u0, v0, omega0]

    h_fall = numerics.H_fall_factor * plate.L

    # Adaptive cutoff time to prevent premature termination during slow falls
    if t_max_override is not None:
        t_max = t_max_override
    else:
        t_max = plate.adaptive_t_max(fluid, coeffs, numerics)

    # Termination event when plate reaches target fall depth: Y(t) <= Y0 - H_fall
    target_y = y0[1] - h_fall

    def bottom_hit_event(t: float, state: np.ndarray) -> float:
        return state[1] - target_y

    bottom_hit_event.terminal = True
    bottom_hit_event.direction = -1

    sol = solve_ivp(
        fun=model.rhs,
        t_span=(0.0, t_max),
        y0=y0,
        method=numerics.integrator,
        rtol=numerics.rtol,
        atol=numerics.atol,
        events=[bottom_hit_event],
        dense_output=True
    )

    t_end = sol.t[-1]
    # Sample uniformly at dt_out for post-processing and analysis
    dt = numerics.dt_out
    n_pts = max(int(math.ceil(t_end / dt)) + 1, 2)
    t_eval = np.linspace(0.0, t_end, n_pts)
    y_eval = sol.sol(t_eval)

    X = y_eval[0, :]
    Y = y_eval[1, :]
    theta = y_eval[2, :]
    u = y_eval[3, :]
    v = y_eval[4, :]
    omega = y_eval[5, :]

    # Lab velocity kinematics
    cos_th = np.cos(theta)
    sin_th = np.sin(theta)
    v_X = u * cos_th - v * sin_th
    v_Y = u * sin_th + v * cos_th
    speed = np.hypot(u, v)

    # Check if bottom event was triggered
    reached_bottom = bool(len(sol.t_events[0]) > 0)
    timed_out = (not reached_bottom) and (t_end >= t_max - 1e-6)

    return TrajectoryResult(
        plate=plate,
        fluid=fluid,
        coeffs=coeffs,
        numerics=numerics,
        t=t_eval,
        X=X,
        Y=Y,
        theta=theta,
        u=u,
        v=v,
        omega=omega,
        v_X=v_X,
        v_Y=v_Y,
        speed=speed,
        reached_bottom=reached_bottom,
        timed_out=timed_out,
        H_fall=h_fall,
        t_max=t_max
    )
