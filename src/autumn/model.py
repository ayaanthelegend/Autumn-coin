"""Dynamical model of 2D falling plate / coin cross-section.

Reference:
    Andersen, A., Pesavento, U., & Wang, Z. J. (2005).
    Unsteady aerodynamics of fluttering and tumbling plates.
    Journal of Fluid Mechanics, 541, 65-90. Section 2.
"""

from __future__ import annotations

import math
from typing import Sequence, Tuple
import numpy as np

from autumn.added_mass import added_mass_components
from autumn.forces import (
    compute_circulation,
    compute_viscous_forces_and_torque,
)
from autumn.params import Coefficients, FluidParams, PlateParams


class AutumnModel:
    r"""Coupled 2D quasi-steady rigid-body equations of motion.

    State vector:
        state = [X, Y, theta, u, v, omega]
        - (X, Y): Lab frame position (Y is vertical upward, gravity acts in -Y direction) [m]
        - theta: Angle of major axis from +X axis [rad]
        - (u, v): Body frame velocity components (u along major axis, v along minor axis) [m/s]
        - omega: Angular velocity d(theta)/dt [rad/s]

    Equations:
        Kinematics:
            dX/dt = u \cos\theta - v \sin\theta
            dY/dt = u \sin\theta + v \cos\theta
            d\theta/dt = \omega

        Dynamics (Kirchhoff equations with quasi-steady hydrodynamic forces):
            (m + m_{11}) \dot{u} = (m + m_{22}) v \omega - \Gamma v - F_u - (m - m_f) g \sin\theta
            (m + m_{22}) \dot{v} = -(m + m_{11}) u \omega + \Gamma u - F_v - (m - m_f) g \cos\theta
            (I + I_a) \dot{\omega} = (m_{11} - m_{22}) u v - \tau
    """

    def __init__(
        self,
        plate: PlateParams,
        fluid: FluidParams,
        coeffs: Coefficients,
        enable_drag: bool = True,
        enable_circulation: bool = True,
        enable_torque: bool = True,
        enable_gravity: bool = True,
    ):
        self.plate = plate
        self.fluid = fluid
        self.coeffs = coeffs
        self.enable_drag = enable_drag
        self.enable_circulation = enable_circulation
        self.enable_torque = enable_torque
        self.enable_gravity = enable_gravity

        # Solid masses and inertia
        self.m = plate.mass
        self.m_f = plate.mass_fluid(fluid.rho_f)
        self.I = plate.I_solid

        # Potential flow added mass
        self.m11, self.m22, self.I_a = added_mass_components(
            plate.a, plate.b, fluid.rho_f
        )

        # Total virtual mass and virtual inertia
        self.M_u = self.m + self.m11
        self.M_v = self.m + self.m22
        self.I_tot = self.I + self.I_a

    def rhs(self, t: float, state: Sequence[float]) -> np.ndarray:
        """Compute time derivative of the 6-element state vector d(state)/dt."""
        X, Y, theta, u, v, omega = state

        # Kinematics
        cos_th = math.cos(theta)
        sin_th = math.sin(theta)
        dX_dt = u * cos_th - v * sin_th
        dY_dt = u * sin_th + v * cos_th
        dtheta_dt = omega

        # Circulation and aerodynamic forces
        if self.enable_circulation:
            gamma = compute_circulation(u, v, omega, self.plate.L, self.coeffs)
        else:
            gamma = 0.0

        if self.enable_drag or self.enable_torque:
            f_u_calc, f_v_calc, tau_calc = compute_viscous_forces_and_torque(
                u, v, omega, self.plate.L, self.fluid.rho_f, self.coeffs
            )
            f_u = f_u_calc if self.enable_drag else 0.0
            f_v = f_v_calc if self.enable_drag else 0.0
            tau = tau_calc if self.enable_torque else 0.0
        else:
            f_u = 0.0
            f_v = 0.0
            tau = 0.0

        # Gravity and buoyancy
        if self.enable_gravity:
            buoyant_weight = (self.m - self.m_f) * self.fluid.g
            g_u = buoyant_weight * sin_th
            g_v = buoyant_weight * cos_th
        else:
            g_u = 0.0
            g_v = 0.0

        # Dynamics (Kirchhoff coupling + external forces)
        # (m + m11) du/dt = (m + m22) v omega - Gamma v - F_u - (m - m_f) g sin(theta)
        du_dt = (self.M_v * v * omega - gamma * v - f_u - g_u) / self.M_u

        # (m + m22) dv/dt = -(m + m11) u omega + Gamma u - F_v - (m - m_f) g cos(theta)
        dv_dt = (-self.M_u * u * omega + gamma * u - f_v - g_v) / self.M_v

        # (I + I_a) domega/dt = (m11 - m22) u v - tau
        domega_dt = ((self.m11 - self.m22) * u * v - tau) / self.I_tot

        return np.array([dX_dt, dY_dt, dtheta_dt, du_dt, dv_dt, domega_dt], dtype=np.float64)

    def kinetic_energy(self, state: Sequence[float]) -> float:
        r"""Compute total kinetic energy T (rigid body + fluid potential flow).

        T = 0.5 * (m + m11) u^2 + 0.5 * (m + m22) v^2 + 0.5 * (I + I_a) omega^2
        """
        _, _, _, u, v, omega = state
        return 0.5 * self.M_u * (u ** 2) + 0.5 * self.M_v * (v ** 2) + 0.5 * self.I_tot * (omega ** 2)

    def potential_energy(self, state: Sequence[float]) -> float:
        r"""Compute net gravitational potential energy (accounting for buoyancy).

        V = (m - m_f) * g * Y
        """
        _, Y, _, _, _, _ = state
        return (self.m - self.m_f) * self.fluid.g * Y

    def lab_linear_momentum(self, state: Sequence[float]) -> Tuple[float, float]:
        r"""Compute total linear momentum in lab frame P_lab = [P_X, P_Y].

        P_lab = R(theta) * [ (m + m11) u, (m + m22) v ]^T
        P_X = (m + m11) u \cos\theta - (m + m22) v \sin\theta
        P_Y = (m + m11) u \sin\theta + (m + m22) v \cos\theta
        """
        _, _, theta, u, v, _ = state
        p_u = self.M_u * u
        p_v = self.M_v * v
        cos_th = math.cos(theta)
        sin_th = math.sin(theta)
        p_x = p_u * cos_th - p_v * sin_th
        p_y = p_u * sin_th + p_v * cos_th
        return p_x, p_y
