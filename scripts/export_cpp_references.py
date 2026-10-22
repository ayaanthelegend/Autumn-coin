"""Export reference trajectories from Python model for C++ parity tests."""

import csv
import math
import yaml
import numpy as np
from pathlib import Path

from autumn.model import AutumnModel
from autumn.params import Coefficients, FluidParams, PlateParams

ROOT_DIR = Path(__file__).resolve().parent.parent
BASE_CFG = ROOT_DIR / "config" / "base.yaml"
COIN_SETS = ROOT_DIR / "config" / "coin_sets.yaml"
OUT_DIR = ROOT_DIR / "autumn-coin-cpp" / "tests" / "reference"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def rk4_step(model, t, state, dt):
    k1 = model.rhs(t, state)
    k2 = model.rhs(t + 0.5 * dt, state + 0.5 * dt * k1)
    k3 = model.rhs(t + 0.5 * dt, state + 0.5 * dt * k2)
    k4 = model.rhs(t + dt, state + dt * k3)
    return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def export_case(preset_name, theta0_deg, t_max=1.0, dt_phys=1e-4, dt_sample=0.01):
    with open(BASE_CFG, "r") as f:
        base_data = yaml.safe_load(f)
    with open(COIN_SETS, "r") as f:
        coins_data = yaml.safe_load(f)

    fluid_cfg = FluidParams(**base_data["fluid"])
    coeffs_cfg = Coefficients(**base_data["coefficients"])
    p_data = coins_data[preset_name]
    plate_cfg = PlateParams(name=preset_name, rho_s=p_data["rho_s"], L=p_data["L"], h=p_data["h"])

    model = AutumnModel(plate_cfg, fluid_cfg, coeffs_cfg)

    th0_rad = math.radians(theta0_deg)
    state = np.array([0.0, 0.0, th0_rad, 0.0, 0.0, 0.0], dtype=np.float64)

    t = 0.0
    next_sample = 0.0

    csv_file = OUT_DIR / f"ref_{preset_name}_th{int(theta0_deg)}.csv"

    rows = []
    header = ["t", "X", "Y", "theta", "u", "v", "omega"]

    n_steps = int(round(t_max / dt_phys))
    sample_every = int(round(dt_sample / dt_phys))

    for step_i in range(n_steps + 1):
        if step_i % sample_every == 0:
            rows.append([t, state[0], state[1], state[2], state[3], state[4], state[5]])
        state = rk4_step(model, t, state, dt_phys)
        t += dt_phys

    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in rows:
            writer.writerow([f"{v:.9e}" if i > 0 else f"{v:.4f}" for i, v in enumerate(r)])

    print(f"Exported: {csv_file.name} ({len(rows)} samples)")


if __name__ == "__main__":
    export_case("reference_card", 5.0, t_max=1.5)
    export_case("steady_card", 10.0, t_max=1.5)
    export_case("heavy_coin", 45.0, t_max=1.5)
    export_case("light_coin", 30.0, t_max=1.5)
