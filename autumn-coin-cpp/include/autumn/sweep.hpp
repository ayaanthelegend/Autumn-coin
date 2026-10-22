#pragma once

#include "types.hpp"
#include "model.hpp"
#include "tank.hpp"
#include "regime.hpp"
#include "integrator.hpp"
#include <vector>
#include <string>

namespace autumn {

class SimulationRun {
public:
    SimulationRun(const Model& m, const TankConfig& tank, double theta0_deg, double perturb_rad = 1e-6);

    void advance(double sim_seconds, double dt_phys = 1e-4, double dt_sample = 0.001, double t_max = 20.0);
    bool finished() const { return outcome_ != Outcome::Running; }
    Outcome outcome() const { return outcome_; }
    const std::vector<Sample>& samples() const { return samples_; }
    const State& current_state() const { return state_; }
    double current_time() const { return t_; }

    void reset(double theta0_deg, double perturb_rad = 1e-6);

private:
    Model model_;
    TankConfig tank_;
    State state_;
    double t_ = 0.0;
    Outcome outcome_ = Outcome::Running;
    std::vector<Sample> samples_;
    double sample_timer_ = 0.0;
};

struct SweepRow {
    double theta0_deg = 0.0;
    Outcome outcome = Outcome::Bottom;
    double t_fall = 0.0;
    double mean_speed = 0.0;
    double mean_vy = 0.0;
    int n_flips = 0;
    Regime regime = Regime::Steady;
    std::vector<Vec2> trajectory; // X, Y trajectory for ghost overlay
};

std::vector<SweepRow> run_angle_sweep(const Model& model,
                                     const TankConfig& tank,
                                     const RegimeClassifierConfig& classifier,
                                     double theta_min_deg,
                                     double theta_max_deg,
                                     double step_deg,
                                     double perturb_rad = 1e-6,
                                     double dt_phys = 1e-4);

bool export_sweep_csv(const std::string& filepath, const std::vector<SweepRow>& rows);

bool export_trajectory_csv(const std::string& filepath, const std::vector<Sample>& samples);

} // namespace autumn
