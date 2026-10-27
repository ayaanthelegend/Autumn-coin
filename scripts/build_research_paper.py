"""Automated Research Paper Builder (`scripts/build_research_paper.py`).

Generates the publication-ready Word manuscript directly from the humanized text in
`Autumn_Coin_Research_Paper_v3.docx` with all verified data, resolved check notes,
complete mathematical equations, parameter sweep tables, and embedded 300 DPI figures F01-F13.
"""

from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "results" / "paper_figures"


def add_equation(doc: Document, eq_text: str, eq_num: str = ""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(eq_text)
    run.font.name = "Cambria Math"
    run.font.size = Pt(10.5)
    run.italic = True
    if eq_num:
        r_num = p.add_run(f"    ({eq_num})")
        r_num.font.name = "Times New Roman"
        r_num.font.size = Pt(10.5)


def add_figure_block(doc: Document, filename: str, caption: str, width_in: float = 6.0):
    img_path = FIG_DIR / filename
    if img_path.exists():
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(6)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.add_run().add_picture(str(img_path), width=Inches(width_in))
    else:
        p_missing = doc.add_paragraph()
        p_missing.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_m = p_missing.add_run(f"[Figure Placeholder: results/paper_figures/{filename}]")
        r_m.italic = True
        r_m.font.color.rgb = RGBColor(120, 120, 120)

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_cap.paragraph_format.space_before = Pt(2)
    p_cap.paragraph_format.space_after = Pt(10)
    r_cap = p_cap.add_run(caption)
    r_cap.font.name = "Times New Roman"
    r_cap.font.size = Pt(9.5)
    r_cap.italic = True


def add_styled_table(doc: Document, caption: str, headers: list[str], rows: list[list[str]]):
    p_cap = doc.add_paragraph()
    p_cap.paragraph_format.space_before = Pt(8)
    p_cap.paragraph_format.space_after = Pt(3)
    r_cap = p_cap.add_run(caption)
    r_cap.bold = True
    r_cap.font.name = "Times New Roman"
    r_cap.font.size = Pt(10)

    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    for c_idx, h_text in enumerate(headers):
        cell = table.cell(0, c_idx)
        p = cell.paragraphs[0]
        r = p.add_run(h_text)
        r.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(9.0)

    for r_idx, row_vals in enumerate(rows):
        for c_idx, val in enumerate(row_vals):
            cell = table.cell(r_idx + 1, c_idx)
            p = cell.paragraphs[0]
            r = p.add_run(str(val))
            r.font.name = "Times New Roman"
            r.font.size = Pt(9.0)

    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(4)


def build_paper():
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)

    # Normal style
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(6)
    r_t = p_title.add_run(
        "Fluttering and Tumbling of a Falling Coin:\n"
        "A 2D Quasi-Steady Model with a Preliminary SPH Study"
    )
    r_t.bold = True
    r_t.font.size = Pt(15)

    p_auth = doc.add_paragraph()
    p_auth.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_auth.paragraph_format.space_before = Pt(0)
    p_auth.paragraph_format.space_after = Pt(14)
    r_a = p_auth.add_run(
        "Ayaan Bilal\nInternational Young Physicists’ Tournament (IYPT) 2026, Problem 12: “Autumn Coin”"
    )
    r_a.font.size = Pt(10.5)
    r_a.italic = True

    # Abstract
    h_abs = doc.add_heading("Abstract", level=1)
    h_abs.paragraph_format.space_before = Pt(10)
    h_abs.paragraph_format.space_after = Pt(4)
    p_abs = doc.add_paragraph(
        "A coin sinking through water does not fall straight. Depending on how heavy it is, it can flutter from side to side, "
        "tumble over and over in one direction, or move irregularly between the two, much like an autumn leaf. This paper looks at "
        "how these motions depend on the dimensionless moment of inertia I* = ρ_s h / (ρ_f L), the linear rotational damping μ₁, "
        "and the release angle θ₀.\n\n"
        "I use a two-dimensional quasi-steady model of a falling elliptical plate, following Andersen, Pesavento and Wang (2005), "
        "and sort each simulated drop into steady, fluttering, tumbling or mixed motion. With μ₁ = 0.20 the model switches from "
        "fluttering to tumbling at I*_c ≈ 1.21 (h/L = 0.075, θ₀ = 20°), which is inside the experimental value of 1.20 ± 0.10. "
        "With μ₁ = 0.01 the threshold drops by about 19% to 0.97, so the damping term clearly matters. In 50-drop ensembles, "
        "the scatter in landing position grows from 15 mm at I* = 0.80 to 714 mm at I* = 3.50.\n\n"
        "The quasi-steady model has no fluid viscosity, so I also wrote a 2D SPH solver. It shows the expected trend of viscous "
        "damping, but it over-predicts cylinder drag by about five times and is not grid-converged. I therefore treat the SPH "
        "results as qualitative only."
    )
    p_abs.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Section 1
    doc.add_heading("1. Introduction", level=1)
    doc.add_paragraph(
        "When a thin coin or plate sinks in water, the flow around its edges pushes it toward a broadside orientation. "
        "This is the Munk moment, (m₁₁ − m₂₂)uv (Field et al., 1997; Belmonte et al., 1998; Pesavento & Wang, 2004; "
        "Andersen et al., 2005a,b). As the tilted coin slides sideways, vortices shed from its edges create a circulation "
        "and a lift force that stops the slide. What happens next depends on how the coin’s own inertia compares with the "
        "inertia of the water it displaces. A light coin turns back and flutters. A heavier one rotates past the vertical and "
        "tumbles in one direction. Near the boundary between the two, the motion can be irregular."
    )
    doc.add_paragraph(
        "For an elliptical cross-section with chord L = 2a and thickness h = 2b, the motion is controlled by these dimensionless groups:"
    )
    add_equation(doc, "I* = (ρ_s h) / (ρ_f L),    β = h / L,    Re = (ρ_f ⟨|V|⟩ L) / μ,    St = (f L) / ⟨|V|⟩", "1")
    doc.add_paragraph("The velocity and time scales are:")
    add_equation(doc, "U_t = √((ρ_s/ρ_f − 1) g h),    U_0 = U_t / √2,    τ_0 = a / U_0", "2")
    doc.add_paragraph(
        "Defining inertia as I/(mR²) would not work here. For any uniform disk or ellipse it equals a constant (1/4 or 1/2), "
        "so it says nothing about density or thickness. The model is also two-dimensional, which strictly describes a long "
        "plate or card rather than a disk. I use it as a first approximation for a coin and come back to this in Section 5."
    )

    # Section 2
    doc.add_heading("2. Method", level=1)
    doc.add_heading("2.1 The quasi-steady model", level=2)
    doc.add_paragraph(
        "The coin cross-section is an ellipse with semi-axes a = L/2 and b = h/2. Per unit span, its area is A = πab, "
        "its mass is m = ρ_s A, the mass of displaced fluid is m_f = ρ_f A, and its moment of inertia is "
        "I_solid = m(a² + b²)/4. The added-mass terms from potential flow (Lamb, 1932; Andersen et al., 2005a) are:"
    )
    add_equation(doc, "m_11 = π ρ_f b²,    m_22 = π ρ_f a²,    I_a = (1/8) π ρ_f (a² − b²)²", "3")
    doc.add_paragraph(
        "Adding these to the coin gives M_u = m + m₁₁, M_v = m + m₂₂ and I_tot = I_solid + I_a. The state is "
        "q = [X, Y, θ, u, v, ω], where (u, v) is the velocity in the body frame. This is a three-degree-of-freedom system "
        "(X, Y, θ) written as six first-order equations. Following Andersen et al. (2005b):"
    )
    add_equation(doc, "dX/dt = u cosθ − v sinθ,    dY/dt = u sinθ + v cosθ,    dθ/dt = ω", "4")
    add_equation(doc, "M_u (du/dt) = M_v v ω − ρ_f Γ v − F_u − (m − m_f) g sinθ", "5")
    add_equation(doc, "M_v (dv/dt) = −M_u u ω + ρ_f Γ u − F_v − (m − m_f) g cosθ", "6")
    add_equation(doc, "I_tot (dω/dt) = (m_11 − m_22) u v − τ", "7")
    doc.add_paragraph(
        "The angle of attack is α = atan2(−v, u). The circulation, drag and rotational torque are:"
    )
    add_equation(doc, "Γ = −C_T L (u v / |V|) + 0.5 C_R L² ω,    C_T = 1.2,    C_R = π", "8")
    add_equation(doc, "C_D(α) = C_D0 − C_D1 cos 2α,    (F_u, F_v) = 0.5 ρ_f L C_D(α) |V| (u, v),    C_D0 = 1.4,    C_D1 = 1.0", "9")
    add_equation(doc, "τ = 0.5 C_τ ρ_f L⁴ |ω| ω + (π / 8) ρ_f L³ U_char μ₁ ω,    C_τ = 0.07854,    μ₁ = 0.20", "10")
    doc.add_paragraph(
        "Here U_char = U₀ = √((ρ_s/ρ_f − 1) g h / 2). I use ρ_f = 998 kg/m³, μ = 10⁻³ Pa·s and g = 9.81 m/s²."
    )

    doc.add_heading("2.2 Integration and regime classification", level=2)
    doc.add_paragraph(
        "I integrate the equations with the SciPy DOP853 solver (rtol = 10⁻⁹, atol = 10⁻¹¹, output step 0.001 s). "
        "The start of each run is discarded as a transient: times below max(20τ₀, 0.2 t_end) and the first 20% of the "
        "fall height. The rest is accepted only if it is stationary, meaning it is at least 30τ₀ long, covers at least "
        "two cycles, and the oscillation amplitude changes by no more than 15% between the middle and last thirds. "
        "Otherwise the run is labelled “undetermined”. Accepted runs are classified as follows:\n\n"
        "• Steady: the standard deviation of θ is below 1°.\n"
        "• Tumbling: net rotation of at least 720°, with either no reversal larger than 180° or a spin ratio |⟨ω⟩|/⟨|ω|⟩ of at least 0.70.\n"
        "• Fluttering: peak-to-peak θ below 300° and net rotation below 360°.\n"
        "• Mixed: everything else, meaning irregular reversals."
    )

    doc.add_heading("2.3 The SPH solver", level=2)
    doc.add_paragraph(
        "To test the effect of viscosity I wrote a 2D weakly compressible SPH solver in C++20. It uses a Wendland C² kernel "
        "(smoothing length 1.3 dx), a Tait equation of state (γ = 7, c₀ = 10 U_max), Morris laminar viscosity, and ghost boundary "
        "particles (Akinci et al., 2012) with Adami et al. (2012) pressure extrapolation. Time stepping is kick–drift–kick with "
        "Picard iteration for the coupling to the rigid body. I also built a desktop visualizer and a browser version (visualizer.html), "
        "which matched the Python model in my checks."
    )

    # Section 3
    doc.add_heading("3. Results from the quasi-steady model", level=1)
    doc.add_heading("3.1 Two example drops and an energy check", level=2)
    doc.add_paragraph(
        "Fluttering drop. L = 20 mm, h = 1.5 mm, ρ_s = 9000 kg/m³ (I* = 0.676), θ₀ = 15°, fall height 0.800 m. "
        "The coin takes 10.45 s to fall at a mean speed ⟨|V|⟩ of 0.235 m/s (Re ≈ 4690; vertical descent speed 0.077 m/s, "
        "giving ⟨|V|⟩/U_t = 0.683 with U_t = 0.343 m/s). Its angle oscillates in a steady cycle with a peak-to-peak amplitude "
        "of 107.1° (standard deviation 35.3°) at 3.11 Hz, corresponding to a Strouhal number of St = fL/⟨|V|⟩ ≈ 0.265, "
        "and it drifts 13.6 mm sideways."
    )
    doc.add_paragraph(
        "Tumbling drop. L = 24 mm, h = 1.8 mm, ρ_s = 17,964 kg/m³ (I* = 1.35), θ₀ = 20°, fall height 0.960 m. "
        "Because this inertia lies clearly above the critical threshold, rotational momentum carries the plate past the vertical "
        "edge-on position on every half-cycle. The coin completes 12.9 continuous turns in one direction (net rotation −4638°) "
        "in 6.07 s at a mean speed of 0.438 m/s, and persistent lift drives it 1.82 m sideways."
    )
    doc.add_paragraph(
        "As an energy check, kinetic energy, buoyant potential energy and the work lost to viscous dissipation add up to the "
        "available potential energy drop within 1.1 × 10⁻⁵ % on the reference drop, and within 0.12% across the high-inertia sweeps "
        "(Figure 1). This tests the accuracy of the integration. It does not test the physics of the model."
    )
    add_figure_block(
        doc, "F08_energy_budget.png",
        "Figure 1. Energy budget for a falling plate in the quasi-steady model: kinetic energy T(t), buoyant potential energy V_pot(t) "
        "and cumulative dissipated work W_diss(t) closing within 1.1 × 10⁻⁵ % on the reference drop."
    )

    doc.add_heading("3.2 The flutter-to-tumble threshold and the damping coefficient", level=2)
    doc.add_paragraph(
        "The parameter that matters most in the model is the linear rotational damping μ₁. I located the flutter-to-tumble "
        "threshold I*_c by bisection for μ₁ between 0 and 0.20 (Table 1 and Figure 2). The threshold rises steadily with μ₁. "
        "With no linear damping it is 0.951, about 21% below the experimental midpoint of 1.20. With μ₁ = 0.01 it is 0.967 (−19%). "
        "Coins in that range would tumble when they should flutter."
    )
    doc.add_paragraph(
        "With μ₁ = 0.20, the baseline value from Andersen et al. (2005b), the threshold is 1.213. That is 1.1% above the "
        "experimental midpoint and well inside its uncertainty of ±0.10. The damping coefficients in models like this are "
        "calibrated against data, so this agreement is a consistency check, not an independent prediction."
    )
    add_figure_block(
        doc, "F01_regime_vs_istar.png",
        "Figure 2. (a) Regimes over I* from 0.05 to 3.50 at μ₁ = 0.20. (b) Zoom on the transition, I* from 0.95 to 1.90. "
        "(c) Shift of the threshold with μ₁, compared with the experimental bracket [1.10, 1.30] of Andersen et al. (2005b)."
    )
    add_styled_table(
        doc,
        "Table 1. Bisection result for the flutter-to-tumble threshold at different linear damping μ₁ (θ₀ = 20°, h/L = 0.075).",
        ["Damping μ₁", "Threshold I*_c", "Lower bound", "Upper bound", "Bracket width", "Shift vs. 1.20"],
        [
            ["0.00 (none)", "0.9507", "0.9490", "0.9523", "0.0033", "−20.8%"],
            ["0.01", "0.9673", "0.9656", "0.9689", "0.0033", "−19.4%"],
            ["0.05", "1.0204", "1.0188", "1.0221", "0.0033", "−15.0%"],
            ["0.10", "1.0901", "1.0885", "1.0918", "0.0033", "−9.2%"],
            ["0.20 (baseline)", "1.2130", "1.2113", "1.2146", "0.0033", "+1.1%"],
        ]
    )
    add_figure_block(
        doc, "F06_istar_sweep.png",
        "Figure 3. Mean descent speed and sideways drift over a 25-point logarithmic sweep of I*. Both jump in the tumbling window."
    )
    add_figure_block(
        doc, "F07_flutter_spectrum.png",
        "Figure 4. Power spectrum of θ(t) for a light fluttering plate from the initial point of the I* sweep "
        "(I* = 0.05, L = 24 mm, h = 0.96 mm, θ₀ = 5°). The dominant peak is at 0.77 Hz with most of the energy between "
        "0.4 and 1.2 Hz, whereas the heavier, thicker reference coin in Section 3.1 flutters at 3.11 Hz."
    )

    doc.add_heading("3.3 Regime map over I* and Re", level=2)
    doc.add_paragraph(
        "I ran 34 values of I* between 0.05 and 3.50 at four chord lengths (8, 12, 16 and 20 mm), which makes 136 drops. "
        "All used μ₁ = 0.20, a fall height of 100L, and a release angle of 20° plus a perturbation of 10⁻³ rad (Figure 5, Table 2). "
        "The thickness changes along with I* (h/L runs from 0.04 to 0.175, and the density ratio is capped at 20). "
        "Fluttering occurs up to I* = 1.20, tumbling from 1.25 to 1.45, and mixed motion from 1.50 to 2.75. "
        "At I* = 3.0 to 3.5 the map shows fluttering again. This occurs because the map uses h/L = 0.175 and a clean 20° release, "
        "where the thicker plate rocks periodically without tumbling past the vertical in the 100L fall. In contrast, the "
        "high-inertia 50-drop ensemble in Section 3.4 uses a different geometry (h/L ≈ 0.22, ρ_s ≈ 16,000 kg/m³) released near vertical "
        "(θ₀ = 5°) with random velocity noise, which repeatedly tips the coin across the separatrix and produces chaotic scatter."
    )
    doc.add_paragraph(
        "Two points about this map need to be stated plainly. First, Re is not an independent variable in this model. "
        "The coefficients do not depend on Re, so for a given I* and h/L the dimensionless motion is identical at every chord length. "
        "The four chord lengths only change the scale, and with it Re. This is why all counts in Table 2 are multiples of four. "
        "In effect there are 34 distinct runs, and the map shows regimes against I* alone."
    )
    doc.add_paragraph(
        "Second, none of the 136 drops ended in steady broadside descent. To test whether broadside descent is truly unstable "
        "rather than just inaccessible from 20°, I simulated drops starting near broadside with micro-perturbations down to 10⁻⁵ deg. "
        "In every case, the destabilizing Munk moment amplified the initial tilt by over 10⁶ times within a few chord lengths, "
        "growing into full fluttering with an amplitude of ~68°. Steady descent is therefore linearly unstable for coins in water."
    )
    add_figure_block(
        doc, "F02_regime_map_Re_istar.png",
        "Figure 5. Regime map in (I*, Re) for L = 8, 12, 16 and 20 mm."
    )
    add_styled_table(
        doc,
        "Table 2. Regimes found in the 136-drop map (μ₁ = 0.20). The share of drops in each regime depends on how I* was sampled, so I give counts rather than percentages.",
        ["Regime", "I* range", "Drops", "Mean descent speed [m/s]"],
        [
            ["Fluttering", "0.05 to 1.20 and 3.0 to 3.5", "72", "0.0180 to 0.6740"],
            ["Tumbling", "1.25 to 1.45", "20", "0.2239 to 0.5419"],
            ["Mixed", "1.50 to 2.75", "44", "0.2346 to 0.5560"],
            ["Total", "0.05 to 3.50", "136", "0.0180 to 0.6740"],
        ]
    )

    doc.add_heading("3.4 Release angle and landing scatter", level=2)
    doc.add_paragraph(
        "For release angles from 0° to 90°, the coin settles quickly onto the fluttering cycle at low and intermediate "
        "inertia (I* = 0.20 and 0.80; Figure 6). I then dropped 50 coins at each of three values of I*, with small random "
        "perturbations (σ_θ = 0.5°, σ_v = 10⁻⁴ m/s), and recorded where they landed (Figure 7, Table 3)."
    )
    doc.add_paragraph(
        "At I* = 0.80 the landing positions spread by σ_X = 15.3 mm. The motion is a periodic cycle, so the spread is set "
        "mostly by the phase of the cycle at landing, which gives an arcsine-shaped histogram. At I* = 3.50 (where the "
        "ensemble code sets h/L = 0.219, h = 5.25 mm, and ρ_s = 15,968 kg/m³ for L = 24 mm), the spread is 714 mm, which is "
        "46.5 times larger. This is consistent with sensitive dependence on initial conditions in the mixed regime. It does "
        "not prove chaos, which would need a Lyapunov exponent, and heavy coins also drift much farther sideways, which "
        "inflates the spread by itself. A tumbling case near I* = 1.35 would be a useful control."
    )
    add_figure_block(
        doc, "F09_release_angle_sweep.png",
        "Figure 6. Sensitivity to the release angle θ₀ from 0° to 90° at I* = 0.20, 0.80 and 3.50."
    )
    add_figure_block(
        doc, "F10_landing_scatter.png",
        "Figure 7. Landing-position histograms from 50-drop ensembles. At I* = 3.50 the sample standard deviation is 714 mm; the legend shows the population value, 706 mm."
    )
    add_styled_table(
        doc,
        "Table 3. Landing scatter in the 50-drop ensembles (σ_θ = 0.5°, σ_v = 10⁻⁴ m/s). Sample σ_X is given first, population σ in brackets.",
        ["Case", "I*", "Mean X [mm]", "σ_X [mm]", "Min / Max X [mm]", "Span [mm]", "Ratio"],
        [
            ["Low inertia", "0.20", "+76.47", "105.83 (104.8)", "−169.53 / +316.31", "485.84", "6.90×"],
            ["Mid inertia (limit cycle)", "0.80", "+2.80", "15.34 (15.2)", "−20.02 / +23.97", "43.99", "1.00× (baseline)"],
            ["High inertia (mixed)", "3.50", "+105.92", "713.64 (706)", "−1155.16 / +1372.85", "2528.00", "46.52×"],
        ]
    )

    doc.add_heading("3.5 Nine example coins", level=2)
    doc.add_paragraph(
        "Finally I applied the model to nine coins (Table 4, Figure 8). Two are real Pakistani circulation coins, the Rs 10 and "
        "the Rs 5. The other seven are hypothetical design coins in different metals. The lighter coins, including both "
        "Pakistani coins, flutter. A 24 × 3.0 mm brass coin flutters at μ₁ = 0.20 but tumbles at μ₁ = 0.01, and a 24 × 3.5 mm "
        "brass coin tumbles at both. The steel, lead and tungsten coins move irregularly. Each coin has its own h/L, which "
        "differs from the 0.075 used in Section 3.2 (the 3.5 mm brass coin has h/L = 0.146, for example), so their position "
        "relative to the threshold in Table 1 is not a direct comparison."
    )
    add_figure_block(
        doc, "F03_coin_trajectories.png",
        "Figure 8. Trajectories of the nine coins over the first 60 dimensionless time units (a/U₀), with μ₁ = 0.20 and θ₀ = 5° "
        "(plus 10⁻³ rad). Acrylic, aluminium and both Pakistani coins flutter, and so does the 3.0 mm brass coin. The 3.5 mm brass coin "
        "tumbles. Steel, lead and tungsten move irregularly."
    )
    add_styled_table(
        doc,
        "Table 4. The nine example coins, released at 5°, 20°, 45° and 90°, with μ₁ = 0.20 and 0.01.",
        ["Coin", "I*", "ρ_s/ρ_f", "Regime (μ₁ = 0.20)", "Regime (μ₁ = 0.01)", "Effect of damping"],
        [
            ["design_acrylic_24x1.2", "0.0591", "1.18", "fluttering", "undetermined at 5°, fluttering otherwise", "Run too short at 5°"],
            ["design_aluminium_24x1.5", "0.1691", "2.71", "fluttering", "fluttering", "None"],
            ["pk_rs10", "0.4232", "7.19", "fluttering", "fluttering", "None"],
            ["pk_rs5_2002", "0.5999", "6.86", "fluttering", "fluttering", "None"],
            ["design_brass_24x3.0", "1.0646", "8.52", "fluttering", "tumbling", "Flutter to tumble"],
            ["design_brass_24x3.5", "1.2421", "8.52", "tumbling", "tumbling", "None"],
            ["design_steel_24x4.5", "1.4748", "7.87", "mixed", "mixed", "None"],
            ["design_lead_24x3.5", "1.6571", "11.36", "mixed", "mixed", "None"],
            ["design_tungsten_24x3.0", "2.4111", "19.29", "mixed", "mixed", "None"],
        ]
    )

    # Section 4
    doc.add_heading("4. Comparison with the literature and the SPH study", level=1)
    doc.add_heading("4.1 Literature", level=2)
    doc.add_paragraph(
        "The threshold of 1.213 lies within the experimental value of 1.20 ± 0.10 reported by Andersen et al. (2005b). "
        "The flutter Strouhal number in the sweep falls from 0.776 to 0.154 as I* increases, passing through the 0.18 to 0.22 "
        "band of Belmonte et al. (1998) near I* = 0.75 (Figure 9). The reference drop in Section 3.1 gives St ≈ 0.265 at "
        "I* = 0.676 when evaluated using total speed ⟨|V|⟩, which fits squarely into this fluttering range. "
        "Differences from 3D coin experiments (Field et al., 1997) and from the 3D tracking data in the ondrej-cloud "
        "repository are expected, because of tip vortices and rotation out of the plane. A direct comparison with that dataset "
        "is left for future work."
    )
    add_figure_block(
        doc, "F05_literature_comparison.png",
        "Figure 9. Model predictions compared with the descent-speed ratios U_mean/U_t of Andersen et al. (2005b) and the Strouhal band 0.18 to 0.22 of Belmonte et al. (1998)."
    )

    doc.add_heading("4.2 SPH results", level=2)
    doc.add_paragraph(
        "The SPH solver resolves the Navier–Stokes flow directly, so it can show something the ODE cannot: the effect of fluid "
        "viscosity. Figure 10 compares the tilt θ(t) over the first 0.5 s for a fluttering plate (I* = 0.68) and a tumbling plate "
        "(I* = 1.35). The SPH runs reproduce the start of the motion, the first pitching swing and the turnaround, but numerical "
        "dissipation then reduces the amplitude. Figure 11 varies the inlet Reynolds number at I* = 0.65 (Re_in = 25, 100, 300 and 800). "
        "At Re_in = 25, viscosity damps the pitching into a smooth glide at about −60°. At Re_in of 100 or more, the plate keeps shedding "
        "vortices and its pitch keeps reversing."
    )
    doc.add_paragraph(
        "Figure 12 summarises a seven-test verification ladder. The solver does well on the basic tests. The Wendland kernel sums to "
        "one (Test 1). Hydrostatic balance and Archimedes buoyancy are reproduced to 0.0012% (Test 2). Couette flow is within 0.23%, "
        "and the Taylor–Green vortex decays at 0.907 of the true viscosity (Test 3). A very light plate (I* = 0.05) stays stable (Test 6). "
        "It does badly on thin bodies. The drag on a fixed cylinder is about five times too high (C_D = 10.96 at Re = 20 and 8.11 at Re = 40), "
        "and the grid study (Test 7) shows a 23.2% change in descent speed between the L/16 and L/20 grids, because the plate is only 0.9 to 1.5 particles thick."
    )
    doc.add_paragraph(
        "These results limit what the SPH study can claim. The direction of the viscosity trend in Figure 11 is plausible, but with drag "
        "overestimated and no grid convergence I cannot separate physical viscous damping from numerical damping. I use the SPH results "
        "only as a qualitative demonstration that high viscosity suppresses pitching oscillations."
    )
    add_figure_block(
        doc, "F11_sph_vs_ode_tilt.png",
        "Figure 10. Tilt θ(t) from the 2D SPH solver and the 2D ODE over the first 0.50 s of the drop."
    )
    add_figure_block(
        doc, "F12_sph_viscosity_sweep.png",
        "Figure 11. SPH viscosity sweep at I* = 0.65 for Re_in = 25, 100, 300 and 800. At Re_in = 25 the plate settles into a glide at about −60°."
    )
    add_figure_block(
        doc, "F13_sph_validation_problem_tests.png",
        "Figure 12. SPH benchmarks: (a) Test 4, dam-break surge front; (b) Test 5, drag on a fixed cylinder at Re = 20 and 40, where drag is over-predicted; (c) Test 7, grid convergence (23.2% change between L/16 and L/20)."
    )

    # Section 5
    doc.add_heading("5. Limitations", level=1)
    limitations = [
        "Two dimensions. The model describes a long plate, not a disk. Coins also have tip vortices and out-of-plane rotation, which can shift the regime boundaries.",
        "No dependence on Re. The coefficients are constant, so the model cannot show how the regimes change with Reynolds number. That needs a flow solver.",
        "No experiments of my own. All validation is against published data. The nine-coin catalogue is simulated only.",
        "Calibrated damping. The agreement of I*_c with experiment depends on the value of μ₁.",
        "SPH accuracy. The SPH solver is not grid-converged and over-predicts drag on thin bodies, so its results are qualitative.",
    ]
    for lim in limitations:
        p_l = doc.add_paragraph(lim)
        p_l.paragraph_format.space_before = Pt(2)
        p_l.paragraph_format.space_after = Pt(4)

    # Section 6
    doc.add_heading("6. Conclusion", level=1)
    conclusions = [
        "Inertia sorts the motion. In the model, low I* gives fluttering, I* from 1.25 to 1.45 gives tumbling, and I* from 1.5 to 2.75 gives irregular motion. For h/L = 0.075 and θ₀ = 20° the flutter-to-tumble threshold is near I* = 1.2.",
        "Damping matters. With μ₁ = 0.20 the threshold agrees with experiment within its uncertainty. With μ₁ = 0.01 it falls by about 19%, to 0.97.",
        "Sensitivity grows with inertia. No drop released at 20° reached steady descent. Landing scatter rises from 15 mm at I* = 0.80 to 714 mm at I* = 3.50, consistent with sensitive dependence on initial conditions.",
        "Viscosity damps pitching. The SPH solver shows that high viscosity (Re_in = 25) suppresses pitching oscillations, but its boundary-layer resolution is not yet good enough for quantitative results.",
    ]
    for conc in conclusions:
        p_c = doc.add_paragraph(conc)
        p_c.paragraph_format.space_before = Pt(2)
        p_c.paragraph_format.space_after = Pt(4)

    h_ref = doc.add_heading("References", level=2)
    h_ref.paragraph_format.space_before = Pt(12)
    h_ref.paragraph_format.space_after = Pt(4)

    references = [
        "1. S. B. Field, M. Klaus, M. G. Moore and F. Nori, “Chaotic dynamics of falling disks,” Nature 388, 252–254 (1997). https://doi.org/10.1038/40817",
        "2. A. Belmonte, H. Eisenberg and E. Moses, “From flutter to tumble: Inertial drag and Froude similarity in falling paper,” Phys. Rev. Lett. 81, 345–348 (1998). https://doi.org/10.1103/PhysRevLett.81.345",
        "3. U. Pesavento and Z. J. Wang, “Falling paper: Navier–Stokes solutions, model of fluid forces, and center of mass elevation,” Phys. Rev. Lett. 93, 144501 (2004). https://doi.org/10.1103/PhysRevLett.93.144501",
        "4. A. Andersen, U. Pesavento and Z. J. Wang, “Unsteady aerodynamics of fluttering and tumbling plates,” J. Fluid Mech. 541, 65–90 (2005a). https://doi.org/10.1017/S002211200500594X",
        "5. A. Andersen, U. Pesavento and Z. J. Wang, “Analysis of transitions between fluttering, tumbling and steady descent of falling cards,” J. Fluid Mech. 541, 91–104 (2005b). https://doi.org/10.1017/S0022112005005847",
        "6. H. Lamb, Hydrodynamics, 6th ed. (Cambridge University Press, Cambridge, 1932).",
        "7. J. P. Morris, P. J. Fox and Y. Zhu, “Modeling low Reynolds number incompressible flows using SPH,” J. Comput. Phys. 136, 214–226 (1997).",
        "8. N. Akinci, M. Ihmsen, G. Akinci, B. Solenthaler and M. Teschner, “Versatile rigid-fluid coupling for incompressible SPH,” ACM Trans. Graph. 31(4), 62 (2012).",
        "9. S. Adami, X. Y. Hu and N. A. Adams, “A generalized wall boundary condition for smoothed particle hydrodynamics,” J. Comput. Phys. 231, 7057–7075 (2012).",
        "10. O. Novotný, V. Přibyl and M. Ambros (Team Olomoucké srnky), “autumn-coin: 3D stereo tracking and quasi-steady simulation of coins falling through water,” GitHub repository (MIT License), https://github.com/ondrej-cloud/autumn-coin",
    ]
    for ref in references:
        p_r = doc.add_paragraph(ref)
        p_r.paragraph_format.space_before = Pt(2)
        p_r.paragraph_format.space_after = Pt(3)

    out_file = ROOT / "Autumn_Coin_Research_Paper_final.docx"
    doc.save(str(out_file))
    print(f"[SUCCESS] Generated final research paper at: {out_file}")

    # Also attempt to update the other standard file names if unlocked
    for secondary_name in ["Autumn_Coin_Research_Paper_updated.docx", "Autumn_Coin_Research_Paper.docx"]:
        sec_path = ROOT / secondary_name
        try:
            doc.save(str(sec_path))
            print(f"[SUCCESS] Also updated: {sec_path}")
        except PermissionError:
            pass


if __name__ == "__main__":
    build_paper()
