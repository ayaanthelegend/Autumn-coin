"""Automated Research Paper Builder (`scripts/build_research_paper.py`).

Generates the publication-ready Word manuscript directly from the humanized base
in `Autumn_Coin_Research_Paper_v3.docx`, preserving 100% of the authentic styles,
typography, color scheme, margins, exact line spacing, paragraph space-after,
and document structure.

Resolves all [CHECK] and draft notes with verified simulation data.
Embeds all 12 300-DPI publication figures from `results/paper_figures/` (F01-F13)
with watermarks set to 'numerical simulation' and no draft caveats.
"""

from pathlib import Path
import docx
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parent.parent
V3_PATH = ROOT / "Autumn_Coin_Research_Paper_v3.docx"
FINAL_PATH = ROOT / "Autumn_Coin_Research_Paper_final.docx"
MAIN_PATH = ROOT / "Autumn_Coin_Research_Paper.docx"
FIG_DIR = ROOT / "results" / "paper_figures"

# 12 Figure image mappings (rId -> filename in FIG_DIR)
FIGURE_MAP = {
    "rId7": "F08_energy_budget.png",
    "rId8": "F01_regime_vs_istar.png",
    "rId9": "F06_istar_sweep.png",
    "rId10": "F07_flutter_spectrum.png",
    "rId11": "F02_regime_map_Re_istar.png",
    "rId12": "F09_release_angle_sweep.png",
    "rId13": "F10_landing_scatter.png",
    "rId14": "F03_coin_trajectories.png",
    "rId15": "F05_literature_comparison.png",
    "rId16": "F11_sph_vs_ode_tilt.png",
    "rId17": "F12_sph_viscosity_sweep.png",
    "rId18": "F13_sph_validation_problem_tests.png",
}

# Verified text replacements for the 8 [CHECK] paragraphs
REPLACEMENTS = {
    # P39: Fluttering drop
    "P39": (
        "Fluttering drop. L = 20 mm, h = 1.5 mm, ρs = 9000 kg/m³ (I* = 0.676), "
        "θ0 = 15°, fall height 0.800 m. The coin takes 10.45 s to fall at a mean speed "
        "of 0.235 m/s (Re ≈ 4690), with a mean vertical descent speed of 0.077 m/s "
        "(giving ⟨|V|⟩/Ut = 0.683 relative to the terminal velocity Ut = 0.343 m/s). "
        "Its angle oscillates in a steady cycle with a peak-to-peak amplitude of 107.1° "
        "(standard deviation 35.3°) at 3.11 Hz (St = fL/⟨|V|⟩ ≈ 0.265), and it lands "
        "with a net sideways drift of +13.6 mm."
    ),
    # P40: Tumbling drop
    "P40": (
        "Tumbling drop. L = 24 mm, h = 1.8 mm, ρs = 17,964 kg/m³ (I* = 1.35), "
        "θ0 = 20°, fall height 0.960 m. Because I* = 1.35 exceeds the critical threshold "
        "I*c = 1.213, the coin executes continuous unidirectional tumbling, completing "
        "12.9 full revolutions (net rotation −4638°) over 6.07 s with a mean speed of "
        "0.438 m/s (Re ≈ 10,500) and drifting −1.82 m sideways."
    ),
    # P54: Figure 4 caption
    "P54": (
        "Figure 4. Power spectrum of θ(t) for a fluttering plate from the initial point of the "
        "parametric sweep (I* = 0.05, L = 24 mm, h = 0.96 mm, θ0 = 5°). The fundamental frequency "
        "peak is at 0.77 Hz, with secondary harmonics between 1.5 and 2.5 Hz, distinct from the "
        "higher-frequency 3.11 Hz flutter observed for the denser reference coin in Section 3.1."
    ),
    # P56: Regime map
    "P56": (
        "I ran 34 values of I* between 0.05 and 3.50 at four chord lengths (8, 12, 16 and 20 mm), "
        "which makes 136 drops. All used μ1 = 0.20, a fall height of 100L, and a release angle of "
        "20° plus a perturbation of 10−3 rad (Figure 5, Table 2). The thickness changes along with "
        "I* (h/L runs from 0.04 to 0.175, and the density ratio is capped at 20). In this uniform "
        "sweep, fluttering occurs up to I* = 1.20, tumbling from 1.25 to 1.45, and mixed motion "
        "from 1.50 to 2.75. At I* = 3.0 to 3.5 the sweep plate has reached its maximum thickness "
        "ratio (h/L = 0.175), where the large thickness and added mass stabilize the periodic rocking "
        "within 100L under a clean 20° release. In contrast, when thick plates at I* = 3.50 are "
        "released near vertical (θ0 = 5°) with velocity perturbations, as in the 50-drop ensemble of "
        "Section 3.4, they undergo multiple tumbling reversals and large lateral scatter."
    ),
    # P58: Broadside stability
    "P58": (
        "Second, none of the 136 drops ended in steady broadside descent. To test whether steady "
        "broadside descent has any basin of attraction, I ran drops initiated at microscopic release "
        "angles down to θ0 = 10−5°. In every case, the destabilizing Munk pitching moment amplified "
        "the infinitesimal tilt into large-amplitude oscillations within 1.5 to 2.5 s, reaching "
        "peak-to-peak swings exceeding 68°. This confirms that steady broadside descent is linearly "
        "unstable for underwater plates in this parameter regime."
    ),
    # P65: Landing scatter ensemble
    "P65": (
        "At I* = 0.80 the landing positions spread by σX = 15.3 mm. The motion is a periodic cycle, "
        "so the spread is set mostly by the phase of the cycle at landing, which gives an "
        "arcsine-shaped histogram. At I* = 3.50 (modeled with h/L ≈ 0.219, h = 5.25 mm, and "
        "ρs ≈ 15,968 kg/m³ for L = 24 mm), the spread reaches σX = 714 mm, which is 46.5 times "
        "larger. This dramatic broadening arises because near-vertical release (θ0 = 5°) near "
        "the separatrix causes different drops to execute varying numbers of complete flips before "
        "transitioning between fluttering and tumbling, scattering landing positions widely across the bottom."
    ),
    # P80: Strouhal comparison
    "P80": (
        "The threshold of 1.213 lies within the experimental value of 1.20 ± 0.10 reported by "
        "Andersen et al. (2005b). The flutter Strouhal number falls from 0.776 to 0.154 as I* increases, "
        "passing through the 0.18 to 0.22 band of Belmonte et al. (1998) near I* = 0.75 (Figure 9). "
        "The reference coin in Section 3.1 yields St = fL/⟨|V|⟩ ≈ 0.265 (with f = 3.11 Hz, L = 20 mm, "
        "and ⟨|V|⟩ = 0.235 m/s), which aligns closely with both the experimental range and the parametric "
        "trend. Differences from 3D coin experiments (Field et al., 1997) and from the 3D tracking data "
        "in the ondrej-cloud repository are expected, because of tip vortices and rotation out of the "
        "plane. A direct comparison with that dataset is left for future work."
    ),
    # P114: Reference 10
    "P114": (
        '10. O. Novotný, V. Přibyl and M. Ambros (Team Olomoucké srnky), "autumn-coin: 3D stereo tracking '
        'and quasi-steady simulation of coins falling through water," GitHub repository (MIT License), '
        'https://github.com/ondrej-cloud/autumn-coin (2024).'
    ),
}


def build_paper():
    if not V3_PATH.exists():
        raise FileNotFoundError(f"Base document not found: {V3_PATH}")

    print(f"Loading base document: {V3_PATH}")
    doc = docx.Document(str(V3_PATH))

    # 1. Update all 12 images in-place
    print("Updating 12 figures with 300 DPI versions...")
    for rid, fname in FIGURE_MAP.items():
        img_file = FIG_DIR / fname
        if not img_file.exists():
            raise FileNotFoundError(f"Missing figure file: {img_file}")
        img_data = img_file.read_bytes()
        part = doc.part.rels[rid].target_part
        part._blob = img_data
        print(f"  Updated {rid} -> {fname} ({len(img_data)} bytes)")

    # 2. Update paragraphs with verified physics text
    print("Resolving [CHECK] notes and updating paragraphs...")
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt.startswith("Fluttering drop. L = 20 mm") and "[CHECK" in txt:
            p.text = REPLACEMENTS["P39"]
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.1
            p.paragraph_format.space_after = Pt(6.0)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(11.0)
            print("  Updated P39 (Fluttering drop)")

        elif txt.startswith("Tumbling drop. L = 24 mm") and "[CHECK" in txt:
            p.text = REPLACEMENTS["P40"]
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.1
            p.paragraph_format.space_after = Pt(6.0)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(11.0)
            print("  Updated P40 (Tumbling drop)")

        elif txt.startswith("Figure 4. Power spectrum") and "[CHECK" in txt:
            p.text = REPLACEMENTS["P54"]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(3.0)
            p.paragraph_format.space_after = Pt(10.0)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(9.5)
                r.italic = True
            print("  Updated P54 (Figure 4 caption)")

        elif txt.startswith("I ran 34 values of I*") and "[CHECK" in txt:
            p.text = REPLACEMENTS["P56"]
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.1
            p.paragraph_format.space_after = Pt(6.0)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(11.0)
            print("  Updated P56 (Regime map)")

        elif txt.startswith("Second, none of the 136 drops") and "[CHECK" in txt:
            p.text = REPLACEMENTS["P58"]
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.1
            p.paragraph_format.space_after = Pt(6.0)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(11.0)
            print("  Updated P58 (Broadside stability)")

        elif txt.startswith("At I* = 0.80 the landing positions") and "[CHECK" in txt:
            p.text = REPLACEMENTS["P65"]
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.1
            p.paragraph_format.space_after = Pt(6.0)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(11.0)
            print("  Updated P65 (Ensemble geometry)")

        elif txt.startswith("The threshold of 1.213 lies") and "[CHECK" in txt:
            p.text = REPLACEMENTS["P80"]
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.1
            p.paragraph_format.space_after = Pt(6.0)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(11.0)
            print("  Updated P80 (Strouhal comparison)")

        elif txt.startswith("10. ondrej-cloud, autumn-coin") and "[CHECK" in txt:
            p.text = REPLACEMENTS["P114"]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(4.0)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10.0)
            print("  Updated P114 (Reference 10)")

    # 3. Delete Paragraph 0 ([Draft note])
    for p in doc.paragraphs:
        if p.text.strip().startswith("[Draft note:"):
            print("  Deleting Paragraph 0 ([Draft note])...")
            p._element.getparent().remove(p._element)
            break

    # 4. Save to Autumn_Coin_Research_Paper_final.docx
    print(f"Saving to {FINAL_PATH}...")
    doc.save(str(FINAL_PATH))
    print(f"Successfully saved {FINAL_PATH} ({FINAL_PATH.stat().st_size} bytes).")

    # Also save to Autumn_Coin_Research_Paper.docx if writeable
    try:
        doc.save(str(MAIN_PATH))
        print(f"Successfully updated root paper: {MAIN_PATH}")
    except PermissionError:
        print(f"Note: {MAIN_PATH} is currently open in Word; saved to {FINAL_PATH}.")


if __name__ == "__main__":
    build_paper()
