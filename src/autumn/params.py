"""Parameter definitions, dataclasses, and configuration loaders for Autumn Coin."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

_VERIFY_WARNED = False

def warn_verify_coefficients_once() -> None:
    """Print confirmation on first use for hydrodynamic coefficients."""
    global _VERIFY_WARNED
    if not _VERIFY_WARNED:
        print("[Autumn Info] Hydrodynamic coefficients: C_T=1.2, C_R=pi, C_D0=1.4, C_D1=1.0, C_tau=pi*mu_2/8=0.07854, mu_1=0.2, mu_2=0.2 (baseline literature values from Andersen et al. 2005b as used in ondrej-cloud implementation (equation number unchecked); mu_1=0.01 is tuned, not from the paper).")
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
    r"""Hydrodynamic force and torque coefficients.
    
    References:
        Andersen, A., Pesavento, U., & Wang, Z. J. (2005a).
        Unsteady aerodynamics of fluttering and tumbling plates.
        J. Fluid Mech. 541, 65-90. DOI: 10.1017/S002211200500594X.
        
        Andersen, A., Pesavento, U., & Wang, Z. J. (2005b).
        Analysis of transitions between fluttering, tumbling and steady descent of falling cards.
        J. Fluid Mech. 541, 91-104. DOI: 10.1017/S0022112005005847.
        Eqs. (3.1)-(3.9): circulation Eq. 3.7, drag Eq. 3.8, torque Eq. 3.9.
        Note: Andersen et al. (2005b) eq. (3.9) gives:
            tau_nu = pi * rho_f * a^4 * ((U/a)*mu_1 + mu_2 * |omega|) * omega
        Standard literature baseline is mu_1 = 0.2, mu_2 = 0.2 (e.g. arXiv:2102.10386).
        With a = L/2 and mu_2 = 0.2, this equates to 0.5 * C_tau * rho_f * L^4 * |omega|*omega
        with C_tau = pi * mu_2 / 8 = 0.0785 (standard strip theory uses 0.075).
        mu_1 = 0.01 is an alternative empirically tuned value.
    """
    C_T: float = 1.2
    C_R: float = math.pi
    C_D0: float = 1.4
    C_D1: float = 1.0
    mu_1: float = 0.2
    mu_2: float = 0.2
    C_tau: float = math.pi * 0.2 / 8.0  # 0.0785398... derived from pi*mu_2/8; 0.075 strip theory is a documented alternative
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
    t_max_factor: float = 5.0
    t_max_min: float = 80.0
    seed: int = 42
    perturbation_rad: float = 0.0
    tank_depth_m: Optional[float] = 0.38

    @classmethod
    def from_config(cls, path: str = "config/base.yaml") -> NumericsParams:
        """Explicitly construct NumericsParams from YAML configuration."""
        p = Path(path)
        if not p.exists():
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        num_data = data.get("numerics", {})
        return cls(**num_data)


@dataclass(frozen=True)
class RegimeClassifierParams:
    """Thresholds for post-processing classification of trajectory regimes."""
    transient_fraction: float = 0.20
    transient_t_min: float = 1.0
    theta_std_steady_deg: float = 1.0
    theta_ptp_steady_deg: float = 2.0
    theta_ptp_flutter_max_deg: float = 300.0
    min_flips_tumble: int = 2
    max_reversal_tumble_deg: float = 180.0
    min_spin_ratio_tumble: float = 0.70


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


def load_coins_yaml(config_path: Optional[str | Path] = None) -> List[PlateParams]:
    """Load enabled coins and design discs from coins.yaml."""
    if config_path is None:
        config_path = get_default_config_path("coins.yaml")
    p = Path(config_path)
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    plates = []
    for item in data.get("coins", []):
        if not item.get("enabled", True):
            continue
        if item.get("kind") == "washer":
            continue
        if item.get("thickness_mm") is None:
            continue

        name = item.get("id", "")
        label = item.get("label", name)
        diameter_mm = float(item["diameter_mm"])
        thickness_mm = float(item["thickness_mm"])
        L = diameter_mm * 1e-3
        h = thickness_mm * 1e-3

        if "rho_s_kgm3" in item and item["rho_s_kgm3"] is not None:
            rho_s = float(item["rho_s_kgm3"])
        elif "mass_g" in item and item["mass_g"] is not None:
            mass_kg = float(item["mass_g"]) * 1e-3
            vol_3d = math.pi * (0.5 * L) ** 2 * h
            rho_s = mass_kg / vol_3d
        else:
            continue

        plates.append(PlateParams(
            name=name,
            rho_s=rho_s,
            L=L,
            h=h,
            notes=label
        ))
    return plates
