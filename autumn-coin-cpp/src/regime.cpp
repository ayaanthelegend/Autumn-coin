#include "autumn/regime.hpp"
#include <cmath>
#include <numeric>
#include <algorithm>

namespace autumn {

Regime classify_regime(const std::vector<Sample>& samples,
                       double H_fall,
                       const RegimeClassifierConfig& cfg,
                       RegimeMetrics* out_metrics,
                       double tau_0) {
    if (samples.empty()) return Regime::Steady;

    const double t_end = samples.back().t;
    const double eff_tau0 = (tau_0 > 0.0) ? tau_0 : 0.05;
    const double t_trans_thresh = (tau_0 > 0.0) ? (cfg.transient_time_units * eff_tau0) : cfg.transient_t_min;
    const double t_transient = std::max(cfg.transient_fraction * t_end, t_trans_thresh);
    const double y0 = samples.front().Y;
    const double transient_depth = cfg.transient_fraction * H_fall;

    std::vector<double> th_crop;
    std::vector<double> om_crop;
    std::vector<double> t_crop;
    th_crop.reserve(samples.size());
    om_crop.reserve(samples.size());
    t_crop.reserve(samples.size());

    for (const auto& s : samples) {
        if (s.t >= t_transient && s.Y <= (y0 - transient_depth)) {
            th_crop.push_back(s.theta);
            om_crop.push_back(s.omega);
            t_crop.push_back(s.t);
        }
    }

    // Fallback if not enough samples
    if (th_crop.size() < 10) {
        th_crop.clear();
        om_crop.clear();
        t_crop.clear();
        for (const auto& s : samples) {
            if (s.t >= 0.5 * t_end) {
                th_crop.push_back(s.theta);
                om_crop.push_back(s.omega);
                t_crop.push_back(s.t);
            }
        }
        if (th_crop.size() < 5) {
            th_crop.clear();
            om_crop.clear();
            t_crop.clear();
            for (const auto& s : samples) {
                th_crop.push_back(s.theta);
                om_crop.push_back(s.omega);
                t_crop.push_back(s.t);
            }
        }
    }

    if (th_crop.empty()) return Regime::Steady;

    // Peak-to-peak and std
    auto minmax_th = std::minmax_element(th_crop.begin(), th_crop.end());
    const double ptp_theta = *minmax_th.second - *minmax_th.first;

    const double mean_th = std::accumulate(th_crop.begin(), th_crop.end(), 0.0) / th_crop.size();
    double sq_diff_sum = 0.0;
    for (double v : th_crop) {
        sq_diff_sum += (v - mean_th) * (v - mean_th);
    }
    const double std_theta = std::sqrt(sq_diff_sum / th_crop.size());

    // Net rotation
    const double delta_th_net = th_crop.back() - th_crop.front();
    const double net_rotation = std::abs(delta_th_net);
    const int n_flips = static_cast<int>(net_rotation / (2.0 * M_PI));

    // Backward excursion
    double max_backward_excursion = 0.0;
    if (delta_th_net >= 0) {
        double run_max = th_crop[0];
        for (double v : th_crop) {
            run_max = std::max(run_max, v);
            max_backward_excursion = std::max(max_backward_excursion, run_max - v);
        }
    } else {
        double run_min = th_crop[0];
        for (double v : th_crop) {
            run_min = std::min(run_min, v);
            max_backward_excursion = std::max(max_backward_excursion, v - run_min);
        }
    }

    double sum_abs_om = 0.0;
    double sum_om = 0.0;
    for (double w : om_crop) {
        sum_abs_om += std::abs(w);
        sum_om += w;
    }
    const double mean_abs_om = sum_abs_om / om_crop.size();
    const double mean_om = sum_om / om_crop.size();
    const double spin_ratio = std::abs(mean_om) / (mean_abs_om + 1e-9);

    const double std_deg = std_theta * (180.0 / M_PI);
    const double ptp_deg = ptp_theta * (180.0 / M_PI);
    const double back_deg = max_backward_excursion * (180.0 / M_PI);

    const double dt_win = t_crop.empty() ? 0.0 : (t_crop.back() - t_crop.front());
    const double win_tu = dt_win / eff_tau0;

    int zc = 0;
    for (size_t i = 1; i < om_crop.size(); ++i) {
        if ((om_crop[i - 1] < 0.0 && om_crop[i] > 0.0) || (om_crop[i - 1] > 0.0 && om_crop[i] < 0.0)) {
            zc++;
        }
    }
    const double net_turns = net_rotation / (2.0 * M_PI);
    const double n_cycles = std::max(net_turns, static_cast<double>(zc) / 2.0);

    if (out_metrics) {
        out_metrics->theta_range_deg = ptp_deg;
        out_metrics->std_theta_deg = std_deg;
        out_metrics->n_flips = n_flips;
        out_metrics->delta_theta_net_deg = delta_th_net * (180.0 / M_PI);
        out_metrics->max_backward_excursion_deg = back_deg;
        out_metrics->spin_ratio = spin_ratio;
        out_metrics->mean_abs_omega = mean_abs_om;
        out_metrics->window_duration_s = dt_win;
        out_metrics->window_time_units = win_tu;
        out_metrics->n_cycles = n_cycles;
        out_metrics->stationarity_err = 0.0;
    }

    // 1. Steady
    if ((std_deg < cfg.theta_std_steady_deg || ptp_deg < cfg.theta_ptp_steady_deg) && ptp_deg < 360.0) {
        const size_t n3 = th_crop.size() / 3;
        if (n3 >= 2) {
            auto minmax2 = std::minmax_element(th_crop.begin() + n3, th_crop.begin() + 2 * n3);
            auto minmax3 = std::minmax_element(th_crop.begin() + 2 * n3, th_crop.end());
            const double ptp2_deg = (*minmax2.second - *minmax2.first) * (180.0 / M_PI);
            const double ptp3_deg = (*minmax3.second - *minmax3.first) * (180.0 / M_PI);
            if (ptp2_deg < cfg.theta_ptp_steady_deg && ptp3_deg < cfg.theta_ptp_steady_deg) {
                return Regime::Steady;
            }
        } else {
            return Regime::Steady;
        }
    }

    // 2. Horizon duration check
    if (win_tu < cfg.min_window_time_units && samples.size() > 5) {
        return Regime::Undetermined;
    }

    // 3. Minimum oscillation cycles check
    if (n_cycles < cfg.min_cycles && samples.size() > 5) {
        return Regime::Undetermined;
    }

    // 4. Stationarity check: middle third vs last third amplitude within stationarity_tolerance
    const size_t n3 = th_crop.size() / 3;
    if (n3 >= 2) {
        double amp2 = 0.0, amp3 = 0.0;
        if (ptp_deg < cfg.theta_ptp_flutter_max_deg && net_rotation < 2.0 * M_PI) {
            auto minmax2 = std::minmax_element(th_crop.begin() + n3, th_crop.begin() + 2 * n3);
            auto minmax3 = std::minmax_element(th_crop.begin() + 2 * n3, th_crop.end());
            amp2 = *minmax2.second - *minmax2.first;
            amp3 = *minmax3.second - *minmax3.first;
        } else {
            auto minmax2 = std::minmax_element(om_crop.begin() + n3, om_crop.begin() + 2 * n3);
            auto minmax3 = std::minmax_element(om_crop.begin() + 2 * n3, om_crop.end());
            amp2 = *minmax2.second - *minmax2.first;
            amp3 = *minmax3.second - *minmax3.first;
        }
        const double stat_err = std::abs(amp3 - amp2) / std::max(amp2, 1e-6);
        if (out_metrics) out_metrics->stationarity_err = stat_err;
        if (stat_err > cfg.stationarity_tolerance) {
            return Regime::Undetermined;
        }
    }

    // 5. Tumbling
    if ((net_rotation >= cfg.min_flips_tumble * 2.0 * M_PI) &&
        (back_deg < cfg.max_reversal_tumble_deg || spin_ratio >= cfg.min_spin_ratio_tumble)) {
        return Regime::Tumbling;
    }

    // 6. Fluttering
    if ((ptp_deg < cfg.theta_ptp_flutter_max_deg) && (net_rotation < 2.0 * M_PI) && (spin_ratio < cfg.min_spin_ratio_tumble)) {
        return Regime::Fluttering;
    }

    // 7. Mixed / Chaotic
    return Regime::Mixed;
}

std::string regime_to_string(Regime r) {
    switch (r) {
        case Regime::Steady: return "Steady";
        case Regime::Fluttering: return "Fluttering";
        case Regime::Tumbling: return "Tumbling";
        case Regime::Mixed: return "Mixed / Chaotic";
        case Regime::Undetermined: return "Undetermined";
    }
    return "Unknown";
}

} // namespace autumn
