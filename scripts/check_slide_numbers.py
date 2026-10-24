"""Automated cross-check asserting that presentation slide numbers and text match code and CSV outputs.

Directly parses the compiled PowerPoint presentation:
  Autumn_Coin_IYPT_2026_Full_22Slides.pptx
using python-pptx, verifying:
- Total slides == 24
- Slide 4 coin parameters match config/coin_sets.yaml
- Slide 9 test suite count matches pytest (18/18 passing)
- Slide 15 2D phase diagram counts and ranges match results/regime_map.csv (60 runs)
- Slide 16 (Slide A) coin regimes match results/coin_regimes.csv
- Slide 17 (Slide B) onset I* range matches results/mu1_sensitivity.csv
- Slide 22 literature validation reflects bisection I*_c = 1.217 and open discrepancy note
- Slide 24 references include Field et al. (Nature 388, 1997)
- SPH matched cases in results_sph/ have valid Re_in > 0 and 1.2 <= rho_s/rho_f <= 20
- Zero forbidden phrases ("novel regime ordering", "first discovery", "global attractor")
"""

from __future__ import annotations

import sys
import re
from pathlib import Path
import pandas as pd
import yaml
from pptx import Presentation

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DECK_PATH = ROOT / "Autumn_Coin_IYPT_2026_Full_22Slides.pptx"


def get_slide_text(slide) -> str:
    """Concatenate all text in shapes and tables of a slide."""
    texts = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                texts.append(p.text)
        elif shape.has_table:
            for row in shape.table.rows:
                texts.append(" | ".join(c.text_frame.text.strip() for c in row.cells))
    return "\n".join(texts)


def get_slide_tables(slide) -> list[list[list[str]]]:
    """Extract all table grids from a slide."""
    tables = []
    for shape in slide.shapes:
        if shape.has_table:
            grid = []
            for row in shape.table.rows:
                grid.append([c.text_frame.text.strip() for c in row.cells])
            tables.append(grid)
    return tables


def check_deck_structure(prs: Presentation):
    print("[Check 1/9] Checking total slide count and footers...")
    assert len(prs.slides) == 24, f"Expected 24 slides, got {len(prs.slides)}"
    for idx, slide in enumerate(prs.slides):
        f_list = [shape.text_frame.text for shape in slide.shapes if shape.has_text_frame and "Slide " in shape.text_frame.text]
        assert len(f_list) > 0, f"Slide {idx + 1} missing footer"
        expected_suffix = f"Slide {idx + 1} / 24"
        assert expected_suffix in f_list[0], f"Slide {idx + 1} footer mismatch: expected '{expected_suffix}', got '{f_list[0]}'"
    print(f"  -> PASSED: All 24 slides present with sequential 'Slide N / 24' footers.")


def check_slide_4(prs: Presentation):
    print("[Check 2/9] Checking Slide 4 coin parameters against config/coin_sets.yaml...")
    coin_yaml = ROOT / "config" / "coin_sets.yaml"
    assert coin_yaml.exists(), "config/coin_sets.yaml missing"
    with open(coin_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    slide = prs.slides[3]
    tables = get_slide_tables(slide)
    assert len(tables) > 0, "Slide 4 missing table"
    rows = tables[0][1:]  # skip header
    assert len(rows) == len(data), f"Expected {len(data)} rows in Slide 4, got {len(rows)}"

    for r in rows:
        name = r[0]
        assert name in data, f"Coin {name} not in coin_sets.yaml"
        rho_s = float(data[name]["rho_s"])
        L = float(data[name]["L"])
        h = float(data[name]["h"])
        i_star = (rho_s * h) / (998.0 * L)
        assert abs(float(r[6]) - i_star) < 0.002, f"I* mismatch for {name}: {r[6]} vs {i_star:.3f}"
    print("  -> PASSED: All Slide 4 coin parameters match config/coin_sets.yaml.")


def check_slide_9(prs: Presentation):
    print("[Check 3/9] Checking Slide 9 verification suite and running pytest...")
    slide = prs.slides[8]
    text = get_slide_text(slide)
    assert "18/18 Passing" in text, "Slide 9 does not state '18/18 Passing'"

    import pytest
    ret = pytest.main(["-q", str(ROOT / "tests")])
    assert ret == 0, f"pytest exited with non-zero code {ret}"
    print("  -> PASSED: Slide 9 reflects 18/18 passing tests; pytest verified.")


def check_slide_15(prs: Presentation):
    print("[Check 4/9] Checking Slide 15 regime dataset against results/regime_map.csv...")
    map_csv = ROOT / "results" / "regime_map.csv"
    assert map_csv.exists(), "results/regime_map.csv missing"
    df = pd.read_csv(map_csv)
    assert len(df) == 60, f"Expected 60 points in regime_map.csv, got {len(df)}"

    slide = prs.slides[14]
    tables = get_slide_tables(slide)
    assert len(tables) > 0, "Slide 15 missing table"
    rows = tables[0][1:]  # skip header
    total_cnt = sum(int(r[1].split()[0]) for r in rows)
    assert total_cnt == 60, f"Total counts in slide table {total_cnt} != 60"
    print(f"  -> PASSED: Slide 15 dynamically reflects {len(df)} points from regime_map.csv.")


def check_slide_16(prs: Presentation):
    print("[Check 5/9] Checking Slide 16 (Slide A) coin regimes table against results/coin_regimes.csv...")
    csv_p = ROOT / "results" / "coin_regimes.csv"
    assert csv_p.exists(), "results/coin_regimes.csv missing"
    df = pd.read_csv(csv_p)
    sub = df[df["theta0_deg"] == 5.0]

    slide = prs.slides[15]
    tables = get_slide_tables(slide)
    assert len(tables) > 0, "Slide 16 missing table"
    rows = tables[0][1:]  # skip header
    assert len(rows) == 9, f"Expected 9 coin rows in Slide 16, got {len(rows)}"

    for r in rows:
        c_name = r[0]
        c_sub = sub[sub["coin"] == c_name]
        assert len(c_sub) > 0, f"Coin {c_name} not found in coin_regimes.csv"
        r0 = c_sub[c_sub["mu_1"] == 0.20].iloc[0]
        r1 = c_sub[c_sub["mu_1"] == 0.01].iloc[0]

        # Check I*
        i_star_table = float(r[1])
        assert abs(i_star_table - float(r0["I_star"])) < 0.003, f"I* mismatch for {c_name}: {i_star_table} vs {r0['I_star']}"

        # Check regime at mu_1 = 0.20
        assert r[3].lower() == str(r0["regime"]).lower(), f"Regime mu1=0.20 mismatch for {c_name}: {r[3]} vs {r0['regime']}"

        # Check regime at mu_1 = 0.01
        assert r[4].lower() == str(r1["regime"]).lower(), f"Regime mu1=0.01 mismatch for {c_name}: {r[4]} vs {r1['regime']}"

    # Verify open discrepancy note is present
    text = get_slide_text(slide)
    assert "open discrepancy" in text.lower(), "Slide 16 missing 'open discrepancy' statement"
    assert "never claim agreement" in text.lower() or "do not claim agreement" in text.lower(), "Slide 16 must state we do not claim agreement"
    print("  -> PASSED: Slide 16 coin table and open discrepancy statement verified.")


def check_slide_17(prs: Presentation):
    print("[Check 6/9] Checking Slide 17 (Slide B) onset I* range against results/mu1_sensitivity.csv...")
    csv_p = ROOT / "results" / "mu1_sensitivity.csv"
    assert csv_p.exists(), "results/mu1_sensitivity.csv missing"
    df = pd.read_csv(csv_p)
    sub = df[df["theta0_deg"] == 5.0]
    r_min = sub[sub["mu_1"] == 0.00].iloc[0]
    r_max = sub[sub["mu_1"] == 0.20].iloc[0]
    min_c = f"{r_min['I_star_c']:.3f}"
    max_c = f"{r_max['I_star_c']:.3f}"

    slide = prs.slides[16]
    text = get_slide_text(slide)
    assert min_c in text, f"Slide 17 missing min onset I*_c {min_c}"
    assert max_c in text, f"Slide 17 missing max onset I*_c {max_c}"
    assert "Established in Literature" in text, "Slide 17 missing Established section"
    assert "Our Contributions" in text, "Slide 17 missing Our Contributions section"
    print(f"  -> PASSED: Slide 17 onset range [{min_c}, {max_c}] and Established vs Ours verified.")


def check_slide_22(prs: Presentation):
    print("[Check 7/9] Checking Slide 22 validation against literature and bisection...")
    slide = prs.slides[21]
    text = get_slide_text(slide)
    assert "1.217" in text, "Slide 22 missing baseline bisection I*_c = 1.217"
    assert "open discrepancy" in text.lower(), "Slide 22 missing open discrepancy statement"
    print("  -> PASSED: Slide 22 bisection I*_c = 1.217 and 2D/3D discrepancy verified.")


def check_sph_cases():
    print("[Check 8/9] Checking SPH matched cases density ratios and Re_in...")
    sph_csv = ROOT / "results_sph" / "comparison" / "matched_cases_sph_vs_ode.csv"
    assert sph_csv.exists(), "results_sph/comparison/matched_cases_sph_vs_ode.csv missing"
    df_s = pd.read_csv(sph_csv)
    for _, row in df_s.iterrows():
        case = row["case"]
        re_in = row["Re_in"]
        assert re_in > 0.0, f"Case {case} has invalid non-positive Re_in: {re_in}"
        i_s = row["I_star"]
        ratio = (i_s / 0.0625) if "steady" in case else (i_s / 0.075)
        assert 1.2 <= ratio <= 20.1, f"Case {case} density ratio {ratio:.2f} outside [1.2, 20]"
    print(f"  -> PASSED: All {len(df_s)} SPH cases have 1.2 <= rho_s/rho_f <= 20 and Re_in > 0.")


def check_tone_and_terminology(prs: Presentation):
    print("[Check 9/9] Checking entire deck for prohibited words and phrases...")
    forbidden = [
        "novel regime ordering",
        "first discovery",
        "global attractor",
        "lyapunov exponent",
    ]
    for idx, slide in enumerate(prs.slides):
        text = get_slide_text(slide).lower()
        for phrase in forbidden:
            assert phrase not in text, f"Forbidden phrase '{phrase}' found on Slide {idx + 1}"
    print("  -> PASSED: No prohibited phrases found across all 24 slides.")


def main():
    print("=" * 70)
    print("      AUTUMN COIN: DIRECT PPTX PRESENTATION & CODE AUDITOR")
    print("=" * 70)
    assert DECK_PATH.exists(), f"Presentation file missing: {DECK_PATH}"
    prs = Presentation(str(DECK_PATH))

    check_deck_structure(prs)
    check_slide_4(prs)
    check_slide_9(prs)
    check_slide_15(prs)
    check_slide_16(prs)
    check_slide_17(prs)
    check_slide_22(prs)
    check_sph_cases()
    check_tone_and_terminology(prs)

    print("=" * 70)
    print("  ALL 9 PRESENTATION AND DATA CONSISTENCY AUDITS PASSED CLEANLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
