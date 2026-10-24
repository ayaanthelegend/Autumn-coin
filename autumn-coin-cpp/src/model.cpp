#include "autumn/model.hpp"
#include <algorithm>
#include <cmath>

namespace autumn {

Model::Model(PlateConfig p, FluidConfig f, CoeffsConfig k)
    : p_(p), f_(f), k_(k) {
    const double a = p_.a();
    const double b = p_.b();

    m_ = p_.mass();
    mf_ = f_.rho_f * p_.area();

    m11_ = f_.rho_f * M_PI * b * b;
    m22_ = f_.rho_f * M_PI * a * a;

    const double diff = a * a - b * b;
    Ia_ = (1.0 / 8.0) * f_.rho_f * M_PI * diff * diff;

    Mu_ = m_ + m11_;
    Mv_ = m_ + m22_;
    It_ = p_.Isolid() + Ia_;

    // Physical linear damping from Andersen et al. (2005b) Eq. 3.9
    double u_char = 0.0;
    const double r_solid = p_.effective_rho_s();
    if (r_solid > f_.rho_f) {
        u_char = std::sqrt((r_solid / f_.rho_f - 1.0) * f_.g * (p_.h * 0.5));
    }
    const double c_lin_phys = (M_PI / 8.0) * f_.rho_f * std::pow(p_.L, 3.0) * u_char * k_.mu_1;
    c_lin_total_ = k_.c_lin + c_lin_phys;
}

State Model::rhs(double /*t*/, const State& s) const {
    const double th = s[2];
    const double u = s[3];
    const double v = s[4];
    const double w = s[5];

    const double c = std::cos(th);
    const double sn = std::sin(th);
    const double V = std::hypot(u, v);
    const double alpha = std::atan2(-v, u);

    const double gamma = (V < k_.eps_V ? 0.0 : -k_.C_T * p_.L * u * v / V)
                       + 0.5 * k_.C_R * p_.L * p_.L * w; // m^2/s

    const double cd = k_.C_D0 - k_.C_D1 * std::cos(2.0 * alpha);
    const double Fu = 0.5 * f_.rho_f * p_.L * cd * V * u;
    const double Fv = 0.5 * f_.rho_f * p_.L * cd * V * v;
    const double tau = 0.5 * k_.C_tau * f_.rho_f * std::pow(p_.L, 4.0) * std::abs(w) * w
                     + c_lin_total_ * w;

    const double W = (m_ - mf_) * f_.g; // buoyant weight

    const double du = (Mv_ * v * w - f_.rho_f * gamma * v - Fu - W * sn) / Mu_;
    const double dv = (-Mu_ * u * w + f_.rho_f * gamma * u - Fv - W * c) / Mv_;
    const double dw = ((m11_ - m22_) * u * v - tau) / It_;

    return { u * c - v * sn, u * sn + v * c, w, du, dv, dw };
}

void Model::lab_forces(const State& s, double& FLx, double& FLy, double& FDx, double& FDy) const {
    const double th = s[2];
    const double u = s[3];
    const double v = s[4];
    const double w = s[5];

    const double c = std::cos(th);
    const double sn = std::sin(th);
    const double dX = u * c - v * sn;
    const double dY = u * sn + v * c;

    const double V = std::hypot(u, v);
    const double alpha = std::atan2(-v, u);

    const double gamma = (V < k_.eps_V ? 0.0 : -k_.C_T * p_.L * u * v / V)
                       + 0.5 * k_.C_R * p_.L * p_.L * w;

    const double cd = k_.C_D0 - k_.C_D1 * std::cos(2.0 * alpha);

    // Circulation lift: perpendicular to velocity V
    FLx = -f_.rho_f * gamma * dY;
    FLy =  f_.rho_f * gamma * dX;

    // Drag: opposing velocity V
    FDx = -0.5 * f_.rho_f * p_.L * cd * V * dX;
    FDy = -0.5 * f_.rho_f * p_.L * cd * V * dY;
}

double Model::kinetic_energy(const State& s) const {
    const double u = s[3];
    const double v = s[4];
    const double w = s[5];
    return 0.5 * Mu_ * u * u + 0.5 * Mv_ * v * v + 0.5 * It_ * w * w;
}

double Model::potential_energy(const State& s) const {
    const double Y = s[1];
    return (m_ - mf_) * f_.g * Y;
}

double Model::total_energy(const State& s) const {
    return kinetic_energy(s) + potential_energy(s);
}

double Model::U_terminal_broadside_est() const {
    // When falling broadside (alpha = pi/2): C_D = C_D0 - C_D1 * cos(pi) = C_D0 + C_D1
    const double cd_broadside = k_.C_D0 + k_.C_D1;
    const double net_weight = (m_ - mf_) * f_.g;
    if (net_weight <= 0.0 || cd_broadside <= 0.0) return 0.0;
    // F_drag = 0.5 * rho_f * L * C_D * U^2 = net_weight
    return std::sqrt((2.0 * net_weight) / (f_.rho_f * p_.L * cd_broadside));
}

} // namespace autumn
