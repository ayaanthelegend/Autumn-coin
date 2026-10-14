"""Parameter definitions, dataclasses, and configuration loaders for Autumn Coin."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

_VERIFY_WARNED = False

def warn_verify_coefficients_once() -> None:
    """Print a one-line warning on first use for coefficients marked VERIFY in README."""
    global _VERIFY_WARNED
    if not _VERIFY_WARNED:
        print("[Autumn Warning] Using hydrodynamic coefficients (C_T=1.2, C_R=pi, C_D0=1.4, C_D1=1.0, C_tau=0.075) with C_tau from strip-theory estimate.")
        _VERIFY_WARNED = True


@dataclass(frozen=True)
class FluidParams:
    """Fluid properties (water at 20 C default).
    
    Attributes:
        rho_f: Fluid density [kg/m^3]
        mu: Dynamic viscosity [Pa*s]
        g: Gravitational acceleration [m/s^2]
    """
    rho_f: float = 998.0
    mu: float = 0.001
    g: float = 9.81


@dataclass(frozen=True)
class Coefficients:
    """Hydrodynamic force and torque coefficients.
    
    Reference: Andersen, Pesavento & Wang, J. Fluid Mech. 541 (2005).
    """
    C_T: float = 1.2
    C_R: float = math.pi
    C_D0: float = 1.4
    C_D1: float = 1.0
    C_tau: float = 0.075  # Strip-theory estimate: C_D / 32 with C_D ~ 2.4
    c_lin: float = 0.0
    eps_V: float = 1.0e-7



@dataclass(frozen=True)
class NumericsParams:
    """Numerical integration parameters."""
    integrator: str = "DOP853"
    rtol: float = 1.0e-9
    atol: float = 1.0e-11
    dt_out: float = 0.001
    H_fall_factor: float = 40.0
    t_max_factor: float = 3.0
    t_max_min: float = 30.0
    seed: int = 42


@dataclass(frozen=True)
class RegimeClassifierParams:
    """Thresholds for post-processing classification of trajectory regimes."""
    transient_fraction: float = 0.1
    theta_range_steady: float = 0.2
    var_theta_steady: float = 0.005
    min_flips_tumble: int = 2


@dataclass(frozen=True)
class PlateParams:
    """Geometric and mass properties of the plate/coin 2D cross-section.
    
    Attributes:
        name: Name identifier of the plate set
        rho_s: Solid density [kg/m^3]
        L: Major axis chord (2*a) [m]
        h: Minor axis thickness (2*b) [m]
        notes: Context or illustrative simulation purpose
    """
    name: str
    rho_s: float
    L: float
    h: float
    notes: str = ""

    @property
    def a(self) -> float:
        """Semi-major axis [m]."""
        return self.L / 2.0

    @property
    def b(self) -> float:
        """Semi-minor axis [m]."""
        return self.h / 2.0

    @property
    def aspect_ratio(self) -> float:
        """Ratio of chord to thickness a/b = L/h."""
        return self.L / self.h

    @property
    def area(self) -> float:
        """Cross-sectional area A = pi * a * b [m^2]."""
        return math.pi * self.a * self.b

    @property
    def mass(self) -> float:
        """Solid mass per unit depth m = rho_s * A [kg/m]."""
        return self.rho_s * self.area

    def mass_fluid(self, rho_f: float) -> float:
        """Displaced fluid mass per unit depth m_f = rho_f * A [kg/m]."""
        return rho_f * self.area

    @property
    def I_solid(self) -> float:
        """Solid moment of inertia per unit depth I = m * (a^2 + b^2) / 4 [kg*m]."""
        return self.mass * (self.a**2 + self.b**2) / 4.0

    def I_star(self, rho_f: float) -> float:
        """Dimensionless moment of inertia I* = (rho_s * h) / (rho_f * L)."""
        return (self.rho_s * self.h) / (rho_f * self.L)

    def U_terminal_broadside_est(self, fluid: FluidParams, coeffs: Coefficients) -> float:
        """Theoretical broadside terminal velocity estimate [m/s].
        
        Equilibrium balance: 0.5 * rho_f * C_D(pi/2) * L * U^2 = (m - m_f) * g
        where C_D(pi/2) = C_D0 + C_D1.
        """
        c_d_broadside = coeffs.C_D0 + coeffs.C_D1
        delta_m = self.mass - self.mass_fluid(fluid.rho_f)
        if delta_m <= 0:
            return 0.01
        num = 2.0 * delta_m * fluid.g
        denom = fluid.rho_f * c_d_broadside * self.L
        return math.sqrt(num / denom)

    def adaptive_t_max(self, fluid: FluidParams, coeffs: Coefficients, numerics: NumericsParams) -> float:
        """Adaptive simulation cutoff time: max(t_max_min, t_max_factor * H_fall / U_terminal)."""
        h_fall = numerics.H_fall_factor * self.L
        u_term = max(self.U_terminal_broadside_est(fluid, coeffs), 0.01)
        calc_t_max = numerics.t_max_factor * (h_fall / u_term)
        return max(numerics.t_max_min, calc_t_max)


@dataclass
class SimulationConfig:
    """Aggregated simulation configuration."""
    fluid: FluidParams = field(default_factory=FluidParams)
    coefficients: Coefficients = field(default_factory=Coefficients)
    numerics: NumericsParams = field(default_factory=NumericsParams)
    regime_classifier: RegimeClassifierParams = field(default_factory=RegimeClassifierParams)
    plate: Optional[PlateParams] = None

    @classmethod
    def from_yaml(cls, base_yaml_path: Optional[str | Path] = None, coin_set_path: Optional[str | Path] = None, plate_name: Optional[str] = None) -> SimulationConfig:
        """Construct configuration from YAML file paths."""
        base_dict = {}
        if base_yaml_path is not None:
            p = Path(base_yaml_path)
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    base_dict = yaml.safe_load(f) or {}

        fluid_data = base_dict.get("fluid", {})
        coeff_data = base_dict.get("coefficients", {})
        num_data = base_dict.get("numerics", {})
        regime_data = base_dict.get("regime_classifier", {})

        fluid = FluidParams(**fluid_data)
        coeffs = Coefficients(**coeff_data)
        numerics = NumericsParams(**num_data)
        classifier = RegimeClassifierParams(**regime_data)

        plate = None
        if coin_set_path is not None and plate_name is not None:
            coin_p = Path(coin_set_path)
            if coin_p.exists():
                with open(coin_p, "r", encoding="utf-8") as f:
                    coins_dict = yaml.safe_load(f) or {}
                if plate_name in coins_dict:
                    entry = coins_dict[plate_name]
                    plate = PlateParams(
                        name=plate_name,
                        rho_s=float(entry["rho_s"]),
                        L=float(entry["L"]),
                        h=float(entry["h"]),
                        notes=str(entry.get("notes", ""))
                    )

        warn_verify_coefficients_once()
        return cls(fluid=fluid, coefficients=coeffs, numerics=numerics, regime_classifier=classifier, plate=plate)


def get_default_config_path(filename: str) -> Path:
    """Resolve config file relative to project root."""
    root = Path(__file__).resolve().parent.parent.parent
    return root / "config" / filename


def load_all_coin_sets(config_path: Optional[str | Path] = None) -> Dict[str, PlateParams]:
    """Load all defined coin sets from YAML."""
    if config_path is None:
        config_path = get_default_config_path("coin_sets.yaml")
    p = Path(config_path)
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    coin_sets = {}
    for name, entry in data.items():
        coin_sets[name] = PlateParams(
            name=name,
            rho_s=float(entry["rho_s"]),
            L=float(entry["L"]),
            h=float(entry["h"]),
            notes=str(entry.get("notes", ""))
        )
    return coin_sets
