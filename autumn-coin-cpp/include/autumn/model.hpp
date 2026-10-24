#pragma once

#include "types.hpp"
#include <cmath>
#include <string>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace autumn {

struct FluidConfig {
    double rho_f = 998.0; // kg/m^3
    double mu = 0.001;    // Pa*s
    double g = 9.81;      // m/s^2

    double nu() const { return (rho_f > 0.0) ? (mu / rho_f) : 0.0; }
};

struct CoeffsConfig {
    double C_T = 1.2;
    double C_R = M_PI;
    double C_D0 = 1.4;
    double C_D1 = 1.0;
    double mu_1 = 0.2; // Baseline literature value; 0.01 is tuned, not from paper
    double mu_2 = 0.2; // Baseline literature value
    double C_tau = M_PI * 0.2 / 8.0; // 0.0785398... derived from pi*mu_2/8; 0.075 strip theory is alternative
    double c_lin = 0.0;
    double eps_V = 1e-7;
};

struct PlateConfig {
    std::string id = "reference_card";
    std::string label = "Reference Card";
    std::string kind = "coin"; // coin | washer
    double rho_s = 9000.0;     // kg/m^3
    double L = 0.020;          // chord / major diameter (m)
    double h = 0.0015;         // thickness / minor diameter (m)
    double mass_g = 0.0;       // optional mass in grams
    std::string material = "brass";
    bool enabled = true;
    std::string source = "illustrative";

    double a() const { return 0.5 * L; }
    double b() const { return 0.5 * h; }
    double area() const { return M_PI * a() * b(); }
    double mass() const {
        if (mass_g > 0.0) return mass_g * 1e-3; // if explicit mass given
        return rho_s * area();
    }
    double effective_rho_s() const {
        if (mass_g > 0.0 && area() > 0.0) return (mass_g * 1e-3) / area();
        return rho_s;
    }
    double Isolid() const { return 0.25 * mass() * (a() * a() + b() * b()); }
    double I_star(double rho_f = 998.0) const {
        return (effective_rho_s() * h) / (rho_f * L);
    }
    double U_t(double rho_f = 998.0, double g = 9.81) const {
        double r = (effective_rho_s() / rho_f) - 1.0;
        return (r > 0.0) ? std::sqrt(r * g * h) : 0.0;
    }
};

class Model {
public:
    Model(PlateConfig p, FluidConfig f, CoeffsConfig k);

    State rhs(double t, const State& s) const;

    void lab_forces(const State& s, double& FLx, double& FLy, double& FDx, double& FDy) const;

    double kinetic_energy(const State& s) const;
    double potential_energy(const State& s) const;
    double total_energy(const State& s) const;

    double U_terminal_broadside_est() const;

    const PlateConfig& plate() const { return p_; }
    const FluidConfig& fluid() const { return f_; }
    const CoeffsConfig& coeffs() const { return k_; }

    double mass() const { return m_; }
    double mass_fluid() const { return mf_; }
    double m11() const { return m11_; }
    double m22() const { return m22_; }
    double Ia() const { return Ia_; }
    double Mu() const { return Mu_; }
    double Mv() const { return Mv_; }
    double Itot() const { return It_; }

private:
    PlateConfig p_;
    FluidConfig f_;
    CoeffsConfig k_;

    double m_ = 0.0;
    double mf_ = 0.0;
    double m11_ = 0.0;
    double m22_ = 0.0;
    double Ia_ = 0.0;
    double Mu_ = 0.0;
    double Mv_ = 0.0;
    double It_ = 0.0;
    double c_lin_total_ = 0.0;
};

} // namespace autumn
