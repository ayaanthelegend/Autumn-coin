"""Acceptance Test 5: Energy budget reconciliation across full drop trajectory."""

import numpy as np
import pytest

from autumn.integrate import simulate_drop
from autumn.metrics import compute_energy_budget
from autumn.params import PlateParams, SimulationConfig


def test_energy_budget_closure_reference_card():
    r"""Acceptance Test 5 (with user amendment 4):
    
    With drag, torque, and circulation work included, the energy budget
    T(t) + V_pot(t) + W_diss(t) reconciles to within 1 percent of the total
    potential energy drop (m - m_f) * g * H_fall over a full drop.
    
    Note: This test verifies numerical and algebraic consistency between the
    forces and the integrator.
    """
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    plate = PlateParams(
        name="reference_card",
        rho_s=1200.0,
        L=0.020,
        h=0.002
    )

    # Release at 15 degrees tilt
    res = simulate_drop(
        plate=plate,
        fluid=cfg.fluid,
        coeffs=cfg.coefficients,
        numerics=cfg.numerics,
        theta0=np.radians(15.0)
    )
    assert res.reached_bottom, "Plate should complete drop to the bottom"

    energy_data = compute_energy_budget(res)
    max_err_pct = energy_data["max_residual_pct"]

    print(f"\nEnergy budget max residual: {max_err_pct:.4f}% (limit: 1.0%)")
    assert max_err_pct < 1.0, f"Energy budget residual {max_err_pct:.3f}% exceeds 1% limit"


def test_energy_budget_closure_heavy_coin():
    """Verify energy budget closes to < 1% for high-inertia heavy coin."""
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    plate = PlateParams(
        name="heavy_coin",
        rho_s=7800.0,
        L=0.024,
        h=0.0018
    )

    res = simulate_drop(
        plate=plate,
        fluid=cfg.fluid,
        coeffs=cfg.coefficients,
        numerics=cfg.numerics,
        theta0=np.radians(30.0)
    )
    assert res.reached_bottom

    energy_data = compute_energy_budget(res)
    max_err_pct = energy_data["max_residual_pct"]
    assert max_err_pct < 1.0, f"Heavy coin energy residual {max_err_pct:.3f}% exceeds 1% limit"
