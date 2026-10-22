"""Pytest suite for C++ SPH solver validation tests (Tests 1 to 7)."""

import subprocess
import sys
from pathlib import Path
import pytest
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
SPH_RUNNER = ROOT_DIR / "cpp_sph" / "bin" / ("sph_runner.exe" if sys.platform == "win32" else "sph_runner")
VAL_DIR = ROOT_DIR / "results_sph" / "validation"

def ensure_runner():
    if not SPH_RUNNER.exists():
        from cpp_sph.build import build_sph
        build_sph()
    assert SPH_RUNNER.exists(), f"Could not find {SPH_RUNNER}"

def test_test1_kernel():
    ensure_runner()
    res = subprocess.run([str(SPH_RUNNER), "--test", "1"], capture_output=True, text=True)
    assert res.returncode == 0, f"Test 1 failed:\n{res.stdout}\n{res.stderr}"
    csv_path = VAL_DIR / "test1_kernel.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert (df["status"] == "PASS").all()

def test_test2_hydrostatic_buoyancy():
    ensure_runner()
    res = subprocess.run([str(SPH_RUNNER), "--test", "2"], capture_output=True, text=True)
    assert res.returncode == 0, f"Test 2 failed:\n{res.stdout}\n{res.stderr}"
    csv_path = VAL_DIR / "test2_hydrostatic_buoyancy.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert (df["status"] == "PASS").all()

def test_test3_viscous_operators():
    ensure_runner()
    res = subprocess.run([str(SPH_RUNNER), "--test", "3"], capture_output=True, text=True)
    assert res.returncode == 0, f"Test 3 failed:\n{res.stdout}\n{res.stderr}"
    csv_path = VAL_DIR / "test3_viscous_operators.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert (df["status"] == "PASS").all()

def test_test4_dam_break():
    ensure_runner()
    res = subprocess.run([str(SPH_RUNNER), "--test", "4"], capture_output=True, text=True)
    assert res.returncode == 0, f"Test 4 failed:\n{res.stdout}\n{res.stderr}"
    csv_path = VAL_DIR / "test4_dam_break.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert len(df) > 0

def test_test5_cylinder_drag():
    ensure_runner()
    res = subprocess.run([str(SPH_RUNNER), "--test", "5"], capture_output=True, text=True)
    assert res.returncode == 0, f"Test 5 failed:\n{res.stdout}\n{res.stderr}"
    csv_path = VAL_DIR / "test5_cylinder_drag.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert (df["status"] == "PASS").all()

def test_test6_low_Istar_stability():
    ensure_runner()
    res = subprocess.run([str(SPH_RUNNER), "--test", "6"], capture_output=True, text=True)
    assert res.returncode == 0, f"Test 6 failed:\n{res.stdout}\n{res.stderr}"
    csv_path = VAL_DIR / "test6_low_Istar_stability.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert len(df) > 10

def test_test7_resolution_study():
    ensure_runner()
    res = subprocess.run([str(SPH_RUNNER), "--test", "7"], capture_output=True, text=True)
    assert res.returncode == 0, f"Test 7 failed:\n{res.stdout}\n{res.stderr}"
    csv_path = VAL_DIR / "test7_resolution_study.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert len(df) == 3
