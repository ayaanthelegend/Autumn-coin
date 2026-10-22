#include "autumn/sweep.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <cmath>

namespace autumn {

SimulationRun::SimulationRun(const Model& m, const TankConfig& tank, double theta0_deg, double perturb_rad)
    : model_(m), tank_(tank) {
    reset(theta0_deg, perturb_rad);
}

void SimulationRun::reset(double theta0_deg, double perturb_rad) {
    double th0 = (theta0_deg * M_PI / 180.0) + perturb_rad;
    state_ = { 0.0, 0.0, th0, 0.0, 0.0, 0.0 };
    t_ = 0.0;
    outcome_ = Outcome::Running;
    samples_.clear();
    sample_timer_ = 0.0;

    // Record initial sample
    Sample s;
    s.t = 0.0;
    s.X = state_[0];
    s.Y = state_[1];
    s.theta = state_[2];
    s.u = state_[3];
    s.v = state_[4];
    s.omega = state_[5];
    s.alpha = std::atan2(-s.v, s.u);
    s.speed = std::hypot(s.u, s.v);
    s.vy = s.u * std::sin(s.theta) + s.v * std::cos(s.theta);
    samples_.push_back(s);
}

void SimulationRun::advance(double sim_seconds, double dt_phys, double dt_sample, double t_max) {
    if (finished()) return;

    double elapsed = 0.0;
    const int max_substeps = 10000;
    int step_i = 0;

    while (elapsed < sim_seconds && step_i < max_substeps && outcome_ == Outcome::Running) {
        state_ = rk4_step(model_, t_, state_, dt_phys);
        t_ += dt_phys;
        elapsed += dt_phys;
        sample_timer_ += dt_phys;
        step_i++;

        // Append sample
        if (sample_timer_ >= dt_sample) {
            sample_timer_ = 0.0;
            Sample s;
            s.t = t_;
            s.X = state_[0];
            s.Y = state_[1];
            s.theta = state_[2];
            s.u = state_[3];
            s.v = state_[4];
            s.omega = state_[5];
            s.alpha = std::atan2(-s.v, s.u);
            s.speed = std::hypot(s.u, s.v);
            s.vy = s.u * std::sin(s.theta) + s.v * std::cos(s.theta);
            samples_.push_back(s);
        }

        // Check termination conditions
        outcome_ = check_tank_contact(state_, model_.plate().L, model_.plate().h, tank_);
        if (t_ >= t_max && outcome_ == Outcome::Running) {
            outcome_ = Outcome::Timeout;
        }
    }
}

std::vector<SweepRow> run_angle_sweep(const Model& model,
                                     const TankConfig& tank,
                                     const RegimeClassifierConfig& classifier,
                                     double theta_min_deg,
                                     double theta_max_deg,
                                     double step_deg,
                                     double perturb_rad,
                                     double dt_phys) {
    std::vector<SweepRow> results;
    if (step_deg <= 0.0) step_deg = 15.0;

    for (double th = theta_min_deg; th <= theta_max_deg + 1e-4; th += step_deg) {
        SimulationRun run(model, tank, th, perturb_rad);
        // Integrate until finished or timeout
        run.advance(30.0, dt_phys, 0.002, 30.0);

        SweepRow row;
        row.theta0_deg = th;
        row.outcome = run.outcome();
        row.t_fall = run.current_time();

        const auto& samples = run.samples();
        row.trajectory.reserve(samples.size());
        for (const auto& s : samples) {
            row.trajectory.push_back({s.X, s.Y});
        }

        // Post-transient metrics
        RegimeMetrics rm;
        row.regime = classify_regime(samples, tank.water_height, classifier, &rm);
        row.n_flips = rm.n_flips;

        double sum_spd = 0.0;
        double sum_vy = 0.0;
        size_t count = 0;
        const double t_trans = std::max(0.20 * row.t_fall, 0.5);
        for (const auto& s : samples) {
            if (s.t >= t_trans) {
                sum_spd += s.speed;
                sum_vy += std::abs(s.vy);
                count++;
            }
        }
        row.mean_speed = count > 0 ? (sum_spd / count) : 0.0;
        row.mean_vy = count > 0 ? (sum_vy / count) : 0.0;

        results.push_back(row);
    }
    return results;
}

bool export_sweep_csv(const std::string& filepath, const std::vector<SweepRow>& rows) {
    std::ofstream ofs(filepath);
    if (!ofs.is_open()) return false;

    ofs << "theta0_deg,outcome,t_fall_s,mean_speed_m_s,mean_vy_m_s,n_flips,regime\n";
    for (const auto& r : rows) {
        std::string out_str = (r.outcome == Outcome::Bottom) ? "Bottom" :
                              (r.outcome == Outcome::Wall) ? "Wall" : "Timeout";
        ofs << std::fixed << std::setprecision(2) << r.theta0_deg << ","
            << out_str << ","
            << std::setprecision(4) << r.t_fall << ","
            << std::setprecision(4) << r.mean_speed << ","
            << std::setprecision(4) << r.mean_vy << ","
            << r.n_flips << ","
            << regime_to_string(r.regime) << "\n";
    }
    return true;
}

bool export_trajectory_csv(const std::string& filepath, const std::vector<Sample>& samples) {
    std::ofstream ofs(filepath);
    if (!ofs.is_open()) return false;

    ofs << "t,X,Y,theta,u,v,omega,alpha,speed,vy\n";
    for (const auto& s : samples) {
        ofs << std::scientific << std::setprecision(8)
            << s.t << "," << s.X << "," << s.Y << ","
            << s.theta << "," << s.u << "," << s.v << ","
            << s.omega << "," << s.alpha << "," << s.speed << "," << s.vy << "\n";
    }
    return true;
}

} // namespace autumn
