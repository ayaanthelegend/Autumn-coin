#pragma once

#include "types.hpp"
#include <vector>
#include <string>

namespace autumn {

struct RegimeClassifierConfig {
    double transient_fraction = 0.20;
    double transient_t_min = 1.0;
    double transient_time_units = 20.0;
    double min_window_time_units = 30.0;
    double min_cycles = 2.0;
    double stationarity_tolerance = 0.15;
    double theta_std_steady_deg = 1.0;
    double theta_ptp_steady_deg = 2.0;
    double theta_ptp_flutter_max_deg = 300.0;
    int min_flips_tumble = 2;
    double max_reversal_tumble_deg = 180.0;
    double min_spin_ratio_tumble = 0.70;
};

struct RegimeMetrics {
    double theta_range_deg = 0.0;
    double std_theta_deg = 0.0;
    int n_flips = 0;
    double delta_theta_net_deg = 0.0;
    double max_backward_excursion_deg = 0.0;
    double spin_ratio = 0.0;
    double mean_abs_omega = 0.0;
    double window_duration_s = 0.0;
    double window_time_units = 0.0;
    double n_cycles = 0.0;
    double stationarity_err = 0.0;
};

Regime classify_regime(const std::vector<Sample>& samples,
                       double H_fall,
                       const RegimeClassifierConfig& cfg,
                       RegimeMetrics* out_metrics = nullptr,
                       double tau_0 = 0.05);

std::string regime_to_string(Regime r);

} // namespace autumn
