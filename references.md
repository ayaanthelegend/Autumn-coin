# Primary Literature References & Bibliographic Sources

This document provides complete, peer-reviewed bibliographic citations and contextual annotations for all theoretical formulations, empirical comparisons, and numerical benchmarks used throughout the Autumn Coin project.

---

## 1. Primary Peer-Reviewed Literature

### 1. Dynamics of Falling Plates and Cards
- **Andersen, A., Pesavento, U., & Wang, Z. J. (2005a)**
  *Unsteady aerodynamics of fluttering and tumbling plates.*
  *Journal of Fluid Mechanics*, 541, 65–90.
  DOI: [10.1017/S002211200500594X](https://doi.org/10.1017/S002211200500594X)
  - **Context in project:** Provides 2D Navier–Stokes DNS calculations, dye visualization of vortex wake dipoles, Strouhal pitching frequency scaling ($St \approx 0.18 - 0.22$), and instantaneous force/moment distributions during plate reversal.

- **Andersen, A., Pesavento, U., & Wang, Z. J. (2005b)**
  *Analysis of transitions between fluttering, tumbling and steady descent of falling cards.*
  *Journal of Fluid Mechanics*, 541, 91–104.
  DOI: [10.1017/S0022112005005847](https://doi.org/10.1017/S0022112005005847)
  - **Context in project:** Defines the 6-state coupled 2D Kirchhoff equations of motion (Eqs. 3.1–3.3), quasi-steady circulation model (Eq. 3.7 with $C_T = 1.2$, $C_R = \pi$), drag law (Eq. 3.8 with $C_{D0} = 1.4$, $C_{D1} = 1.0$), and dissipative rotational torque model (Eq. 3.9 with linear viscous damping $\mu_1 = 0.2$ and quadratic damping $\mu_2 = 0.2$). Table 1 provides physical aluminum card drops: Card 1 ($I^* = 1.14$, fluttering) and Card 2 ($I^* = 1.38$, tumbling), establishing the transition band $I^*_c \in [1.10, 1.30]$ with midpoint $1.20$.

- **Pesavento, U., & Wang, Z. J. (2004)**
  *Falling paper: Navier–Stokes solutions, model of fluid forces, and center of mass elevation.*
  *Physical Review Letters*, 93(14), 144501.
  DOI: [10.1103/PhysRevLett.93.144501](https://doi.org/10.1103/PhysRevLett.93.144501)
  - **Context in project:** Derives the energy balance during fluttering and tumbling flight, demonstrating how vortex lift periodically halts downward descent and elevates the center-of-mass relative to steady broadside terminal fall.

- **Belmonte, A., Eisenberg, H., & Moses, E. (1998)**
  *From flutter to tumble: Inertial drag and flutter of flexible and rigid falling leaves.*
  *Physical Review Letters*, 81(2), 345–348.
  DOI: [10.1103/PhysRevLett.81.345](https://doi.org/10.1103/PhysRevLett.81.345)
  - **Context in project:** Experimental flutter frequency scaling across aspect ratios in water/glycerol tanks; provides Strouhal number benchmark ($St \sim 0.20$).

---

### 2. 3D Disks and Coins
- **Field, S. B., Klaus, M., Moore, M. G., & Nori, F. (1997)**
  *Chaotic dynamics of falling disks.*
  *Nature*, 388(6639), 252–254.
  DOI: [10.1038/40817](https://doi.org/10.1038/40817)
  - **Context in project:** Experimental phase diagram for 90 drops of 3D circular disks in water/glycerol mixtures spanning $Re \in [100, 3000]$ and $I^*_\text{disk} \in [10^{-3}, 10^{-1}]$. Identifies four distinct regimes: steady, periodic flutter, chaotic/mixed, and continuous tumbling. Crucially distinguishes 3D disk inertia $I^*_\text{disk} = I_\text{solid} / (\rho_f d^5) = \frac{\pi}{64} \frac{\rho_s h}{\rho_f d}$ from 2D strip inertia $I^* = \frac{\rho_s h}{\rho_f L}$.

---

### 3. Smoothed Particle Hydrodynamics (SPH) & Fluid-Structure Interaction (FSI)
- **Akinci, N., Ihmsen, M., Akinci, G., Solenthaler, B., & Teschner, M. (2012)**
  *Versatile rigid-fluid coupling for incompressible SPH.*
  *ACM Transactions on Graphics (TOG)*, 31(4), Article 62.
  DOI: [10.1145/2185520.2185558](https://doi.org/10.1145/2185520.2185558)
  - **Context in project:** Provides boundary particle discretization with volume scaling $\Psi_b = 1 / \sum_k W_{bk}$, surface pressure extrapolation, and momentum-conserving two-way boundary forces for rigid bodies immersed in SPH fluids.

- **Morris, J. P., Fox, P. J., & Zhu, Y. (1997)**
  *Modeling low Reynolds number incompressible flows using SPH.*
  *Journal of Computational Physics*, 136(1), 214–226.
  DOI: [10.1006/jcph.1997.5776](https://doi.org/10.1006/jcph.1997.5776)
  - **Context in project:** Formulates physical laminar shear stress discretization:
    $$\left(\frac{d\mathbf{v}_i}{dt}\right)_\text{visc} = 2 \nu \sum_j \frac{m_j}{\rho_j} \frac{\mathbf{v}_i - \mathbf{v}_j}{r_{ij}^2 + 0.01 h^2} (\mathbf{r}_{ij} \cdot \nabla_i W_{ij})$$
    which guarantees Galilean invariance and non-negative viscous dissipation.

- **Wendland, H. (1995)**
  *Piecewise polynomial, positive definite and compactly supported radial functions of minimal degree.*
  *Advances in Computational Mathematics*, 4(1), 389–396.
  DOI: [10.1007/BF02123482](https://doi.org/10.1007/BF02123482)
  - **Context in project:** Wendland $C^2$ quintic smoothing kernel:
    $$W(q, h) = \frac{7}{4\pi h^2} \left(1 - \frac{q}{2}\right)^4 (2q + 1), \quad q = \frac{r}{h} \in [0, 2]$$

---

## 4. Open-Source Datasets & Repositories

- **Šrámek, O., et al. (2024)**
  *Autumn Coin: 3D Stereoscopic Tracking & ODE Simulation Dataset.*
  GitHub Repository: [github.com/ondrej-cloud/autumn-coin](https://github.com/ondrej-cloud/autumn-coin)
  License: MIT License.
  - **Context in project:** Provides dual-smartphone 3D stereoscopic tracking of 143 drops of Czech Republic coins (1, 2, 5, 10, 20, 50 CZK) and central-hole washers dropped in a 38 cm water tank. Confirms that real metallic coins lie in the high-$I^*$ tumbling/chaotic regime, while washers with center holes experience lower effective inertia and exhibit fluttering.
