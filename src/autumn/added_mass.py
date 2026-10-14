"""Potential-flow added mass and added moment of inertia for an elliptical cylinder.

Reference:
    Andersen, A., Pesavento, U., & Wang, Z. J. (2005).
    Unsteady aerodynamics of fluttering and tumbling plates.
    Journal of Fluid Mechanics, 541, 65-90. Section 2.
    Lamb, H. (1932). Hydrodynamics (6th ed.). Cambridge University Press, Section 71.
"""

from __future__ import annotations

import math
from typing import Tuple


def added_mass_components(a: float, b: float, rho_f: float) -> Tuple[float, float, float]:
    r"""Compute added mass tensor components and added moment of inertia for an ellipse.

    Equations:
        m_{11} = \rho_f \pi b^2
            Added mass per unit depth along the major axis (direction of chord).
        m_{22} = \rho_f \pi a^2
            Added mass per unit depth along the minor axis (direction of thickness).
        I_a = \frac{1}{8} \rho_f \pi (a^2 - b^2)^2
            Added moment of inertia per unit depth about the central transverse axis.

    Args:
        a: Semi-major axis length [m].
        b: Semi-minor axis length [m].
        rho_f: Fluid density [kg/m^3].

    Returns:
        Tuple of (m11, m22, I_a) in SI units ([kg/m], [kg/m], [kg*m]).
    """
    if a < 0 or b < 0:
        raise ValueError(f"Semi-axes must be non-negative: a={a}, b={b}")
    if rho_f <= 0:
        raise ValueError(f"Fluid density must be positive: rho_f={rho_f}")

    m11 = rho_f * math.pi * (b ** 2)
    m22 = rho_f * math.pi * (a ** 2)
    i_a = rho_f * math.pi * ((a ** 2 - b ** 2) ** 2) / 8.0
    return m11, m22, i_a
