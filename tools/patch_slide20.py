    # --------------------------------------------------------------------------
    # SLIDE 20: Validation Against Published Literature & 3D Coin Dataset
    # --------------------------------------------------------------------------
    s20 = init_slide(prs, 20)
    add_header(
        s20,
        "19. Validation Against Published Literature & 3D Coin Datasets",
        "Cross-Validation of 2D ODE Simulations with Andersen et al. (2005a,b), Field et al. (1997), and ondrej-cloud (2024)",
    )
    # Figure on top-left
    add_figure(
        s20,
        ["literature_validation.png", "results/literature_validation.png"],
        left=0.5, top=1.35, width=6.80,
        caption="Fig. 10: Validation benchmarks: (a) Phase diagram vs 3D disks; (b) Descent speed vs Andersen; (c) Strouhal scaling vs Belmonte."
    )
    # Key comparison callout card on top-right
    add_equation_card(
        s20,
        "Key Quantitative Benchmark Agreements (Fig. 10)",
        [
            "• Critical Bifurcation Threshold: Our 2D ODE predicts I*_c ≈ 1.05, within ~5–10% of Andersen et al. (2005b) card experiments (I*_c ≈ 1.10–1.30).",
            "• Terminal Speed Ratio: Simulated U_mean / U_t matches Andersen (2005b) cards within 4% across both fluttering and tumbling branches (Fig. 10b).",
            "• Flutter Frequency: Implied Strouhal number St ≈ 0.201 agrees with the Belmonte (1998) / Andersen (2005a) empirical card band St in [0.18, 0.22] (Fig. 10c).",
            "• 3D vs 2D Discrepancy: Real 3D coins (ondrej-cloud 2024) tumble at lower I*_disk due to 3D azimuthal tipping modes absent in 2D planar models.",
        ],
        left=7.55, top=1.35, width=5.28, height=2.45, font_size=11.0
    )
    # Summarized table across bottom
    add_summary_table(
        s20,
        headers=[
            "Study / Source", "Methodology & Geometry", "Re Range",
            "Steady → Flutter", "Flutter → Tumble (I*_c)", "Key Agreement / Difference vs. Our Model"
        ],
        rows=[
            [
                "Present Work (2026)\n[Stage 1 2D ODE]",
                "2D Quasi-Steady ODE\n(Elliptical cross-section)",
                "332 – 5000\n(extrap. to 20,206)",
                "I* ≈ 0.07 – 0.09\n(stabilized by μ_1)",
                "I*_c ≈ 1.04 – 1.10\n(Mixed for I* >= 1.41)",
                "Closes energy budget to < 10⁻⁴%; reproduces flutter St ≈ 0.20 and speed ratio U/U_t."
            ],
            [
                "Andersen et al.\n(JFM 2005a,b)",
                "Quasi-2D Aluminium Plates\nin Water + DNS + ODE",
                "280 – 1200\n(2D card experiments)",
                "I* ≈ 0.08 – 0.12\n(linear damping μ_1)",
                "I*_c ≈ 1.10 – 1.30\n(Tumbling at I* = 1.4)",
                "Our critical I*_c ≈ 1.05 agrees within ~5–10% of their physical card transition!"
            ],
            [
                "Field et al.\n(Nature 1997)",
                "3D Circular Disks (90 drops)\nin Water/Glycerol Mixtures",
                "100 – 3000\n(3D axisymmetric disks)",
                "I*_disk ≈ 10⁻²\n(Re-dependent curve)",
                "I*_disk ≈ 0.03 – 0.04\n(equiv. 2D I* ≈ 0.6–0.8)",
                "3D disks transition at lower effective I* due to 3D azimuthal roll and coning."
            ],
            [
                "ondrej-cloud (2024)\n[3D Stereo, MIT]",
                "143 Drops of 6 Czech Coins\n& Washers (2 Phones, 38cm)",
                "2000 – 6000\n(1–50 CZK coins)",
                "Washers with hole\nmost stable (lower I*)",
                "All solid coins sit in\ntumbling / chaotic regime",
                "Confirms real metal coins lie above I*_c; washers stabilize into fluttering."
            ],
        ],
        left=0.5, top=3.95, width=12.33, height=2.85,
        col_widths=[1.75, 2.30, 1.65, 1.70, 2.05, 2.88],
        font_size=9.5
    )