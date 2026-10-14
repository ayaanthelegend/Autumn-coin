"""Hydrodynamic forces and torques for 2D quasi-steady falling plate.

Reference:
    Andersen, A., Pesavento, U., & Wang, Z. J. (2005).
    Unsteady aerodynamics of fluttering and tumbling plates.
    Journal of Fluid Mechanics, 541, 65-90. Sections 2.2 - 2.4.
"""

from __future__ import annotations

import math
from typing import Tuple
from autumn.params import Coefficients, FluidParams


def compute_angle_of_attack(u: float, v: float) -> float:
    r"""Compute angle of attack alpha from body-frame velocity components.

    Convention:
        \alpha = \text{atan2}(-v, u)
        - Major axis is aligned with u (+x_body).
        - Minor axis is aligned with v (+y_body).
        - When plate descends broadside with u=0 and v < 0, -v > 0, so alpha = pi/2 (90 deg).

    Args:
        u: Velocity component along plate chord (major axis) [m/s].
        v: Velocity component along plate thickness (minor axis) [m/s].

    Returns:
        alpha in radians, in the interval (-pi, pi].
    """
    return math.atan2(-v, u)


def compute_circulation(
    u: float,
    v: float,
    omega: float,
    L: float,
    coeffs: Coefficients
) -> float:
    r"""Compute fluid circulation Gamma from translational and rotational velocity.

    Equation:
        \Gamma = -C_T L \frac{u v}{|V|} + 0.5 C_R L^2 \omega
    Note on convention:
        With Kutta-Joukowski lift F_L = rho_f * Gamma * |V| = 0.5 * rho_f * C_L * L * |V|^2,
        we have C_L(alpha) = 2 Gamma / (|V| L) = -2 C_T (u v / |V|^2) = C_T sin(2 alpha).
        This gives a peak lift coefficient of C_{L,max} = C_T = 1.2 at alpha = 45 deg,
        matching standard thin-airfoil/plate aerodynamics at intermediate Re.

    Args:
        u: Body velocity along chord [m/s].
        v: Body velocity along thickness [m/s].
        omega: Angular velocity d(theta)/dt [rad/s].
        L: Plate chord [m].
        coeffs: Hydrodynamic coefficient parameters.

    Returns:
        Gamma: Circulation [m^2/s].
    """
    speed_sq = u * u + v * v
    speed = math.sqrt(speed_sq)

    if speed < coeffs.eps_V:
        trans_term = 0.0
    else:
        trans_term = -coeffs.C_T * L * (u * v / speed)

    rot_term = 0.5 * coeffs.C_R * (L ** 2) * omega
    return trans_term + rot_term



def compute_drag_coefficient(alpha: float, coeffs: Coefficients) -> float:
    r"""Compute angle-of-attack dependent drag coefficient.

    Equation:
        C_D(\alpha) = C_{D0} - C_{D1} \cos(2 \alpha)

    Reference:
        Andersen et al. (2005), eq. (2.9).
    """
    return coeffs.C_D0 - coeffs.C_D1 * math.cos(2.0 * alpha)


def compute_viscous_forces_and_torque(
    u: float,
    v: float,
    omega: float,
    L: float,
    rho_f: float,
    coeffs: Coefficients
) -> Tuple[float, float, float]:
    r"""Compute viscous dissipative drag forces and rotational damping torque.

    Equations:
        F_u = 0.5 \rho_f L C_D(\alpha) |V| u
        F_v = 0.5 \rho_f L C_D(\alpha) |V| v
        \tau = 0.5 C_\tau \rho_f L^4 |\omega| \omega + c_{\text{lin}} \omega

    Reference:
        Andersen et al. (2005), eqs. (2.10) - (2.11).

    Args:
        u: Body velocity along chord [m/s].
        v: Body velocity along thickness [m/s].
        omega: Angular velocity [rad/s].
        L: Plate chord [m].
        rho_f: Fluid density [kg/m^3].
        coeffs: Hydrodynamic coefficients.

    Returns:
        Tuple of (F_u, F_v, tau) in SI units ([N/m], [N/m], [N*m/m]).
    """
    speed = math.hypot(u, v)
    alpha = compute_angle_of_attack(u, v)
    c_d = compute_drag_coefficient(alpha, coeffs)

    f_u = 0.5 * rho_f * L * c_d * speed * u
    f_v = 0.5 * rho_f * L * c_d * speed * v
    tau = 0.5 * coeffs.C_tau * rho_f * (L ** 4) * abs(omega) * omega + coeffs.c_lin * omega

    return f_u, f_v, tau
