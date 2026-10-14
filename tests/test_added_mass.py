"""Acceptance Test 1: Added mass calculations for elliptical cross-section."""

import math
import pytest
from autumn.added_mass import added_mass_components


def test_added_mass_circular_limit():
    """Acceptance Test 1: For a == b (circle), m11 == m22 and I_a == 0."""
    rho_f = 998.0
    radii = [0.001, 0.01, 0.05, 0.5]

    for r in radii:
        m11, m22, i_a = added_mass_components(a=r, b=r, rho_f=rho_f)
        # For a circular cylinder, m11 and m22 must be equal to rho_f * pi * r^2
        expected_m = rho_f * math.pi * (r ** 2)
        assert math.isclose(m11, m22, rel_tol=1e-12), f"Failed for radius {r}: m11={m11}, m22={m22}"
        assert math.isclose(m11, expected_m, rel_tol=1e-12)
        # Added moment of inertia for a circle in potential flow must be strictly zero
        assert math.isclose(i_a, 0.0, abs_tol=1e-15), f"I_a must be zero for circle, got {i_a}"


def test_added_mass_thin_plate_limit():
    """Verify added mass for thin plate: m22 >> m11 and I_a matches thin-limit formula."""
    rho_f = 998.0
    a = 0.012  # chord 24 mm
    b = 0.0009 # thickness 1.8 mm

    m11, m22, i_a = added_mass_components(a=a, b=b, rho_f=rho_f)
    assert m22 > m11
    ratio = m22 / m11
    expected_ratio = (a / b) ** 2
    assert math.isclose(ratio, expected_ratio, rel_tol=1e-12)

    expected_i_a = rho_f * math.pi * ((a**2 - b**2)**2) / 8.0
    assert math.isclose(i_a, expected_i_a, rel_tol=1e-12)


def test_invalid_inputs():
    """Verify ValueError is raised on non-physical inputs."""
    with pytest.raises(ValueError):
        added_mass_components(a=-0.01, b=0.01, rho_f=1000.0)
    with pytest.raises(ValueError):
        added_mass_components(a=0.01, b=-0.01, rho_f=1000.0)
    with pytest.raises(ValueError):
        added_mass_components(a=0.01, b=0.01, rho_f=0.0)
