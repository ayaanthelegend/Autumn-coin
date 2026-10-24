#include "autumn/config.hpp"
#include <yaml-cpp/yaml.h>
#include <iostream>
#include <fstream>

namespace autumn {

bool load_base_config(const std::string& filepath,
                      FluidConfig& fluid,
                      CoeffsConfig& coeffs,
                      RegimeClassifierConfig& classifier) {
    try {
        YAML::Node root = YAML::LoadFile(filepath);

        if (root["fluid"]) {
            auto f = root["fluid"];
            fluid.rho_f = f["rho_f"].as<double>(fluid.rho_f);
            fluid.mu = f["mu"].as<double>(fluid.mu);
            fluid.g = f["g"].as<double>(fluid.g);
        }

        if (root["coefficients"]) {
            auto c = root["coefficients"];
            coeffs.C_T = c["C_T"].as<double>(coeffs.C_T);
            coeffs.C_R = c["C_R"].as<double>(coeffs.C_R);
            coeffs.C_D0 = c["C_D0"].as<double>(coeffs.C_D0);
            coeffs.C_D1 = c["C_D1"].as<double>(coeffs.C_D1);
            coeffs.C_tau = c["C_tau"].as<double>(coeffs.C_tau);
            coeffs.c_lin = c["c_lin"].as<double>(coeffs.c_lin);
            coeffs.mu_1 = c["mu_1"].as<double>(coeffs.mu_1);
            if (c["mu_2"]) coeffs.mu_2 = c["mu_2"].as<double>(coeffs.mu_2);
            coeffs.eps_V = c["eps_V"].as<double>(coeffs.eps_V);
        }

        if (root["regime_classifier"]) {
            auto r = root["regime_classifier"];
            classifier.transient_fraction = r["transient_fraction"].as<double>(classifier.transient_fraction);
            classifier.transient_t_min = r["transient_t_min"].as<double>(classifier.transient_t_min);
            if (r["transient_time_units"]) classifier.transient_time_units = r["transient_time_units"].as<double>(classifier.transient_time_units);
            if (r["min_window_time_units"]) classifier.min_window_time_units = r["min_window_time_units"].as<double>(classifier.min_window_time_units);
            if (r["min_cycles"]) classifier.min_cycles = r["min_cycles"].as<double>(classifier.min_cycles);
            if (r["stationarity_tolerance"]) classifier.stationarity_tolerance = r["stationarity_tolerance"].as<double>(classifier.stationarity_tolerance);
            classifier.theta_std_steady_deg = r["theta_std_steady_deg"].as<double>(classifier.theta_std_steady_deg);
            classifier.theta_ptp_steady_deg = r["theta_ptp_steady_deg"].as<double>(classifier.theta_ptp_steady_deg);
            classifier.theta_ptp_flutter_max_deg = r["theta_ptp_flutter_max_deg"].as<double>(classifier.theta_ptp_flutter_max_deg);
            classifier.min_flips_tumble = r["min_flips_tumble"].as<int>(classifier.min_flips_tumble);
            classifier.max_reversal_tumble_deg = r["max_reversal_tumble_deg"].as<double>(classifier.max_reversal_tumble_deg);
            classifier.min_spin_ratio_tumble = r["min_spin_ratio_tumble"].as<double>(classifier.min_spin_ratio_tumble);
        }

        return true;
    } catch (const std::exception& e) {
        std::cerr << "[Config] Failed to load " << filepath << ": " << e.what() << std::endl;
        return false;
    }
}

std::vector<PlateConfig> load_coin_sets(const std::string& filepath) {
    std::vector<PlateConfig> plates;
    try {
        YAML::Node root = YAML::LoadFile(filepath);
        for (auto it = root.begin(); it != root.end(); ++it) {
            std::string id = it->first.as<std::string>();
            YAML::Node node = it->second;

            PlateConfig p;
            p.id = id;
            p.label = id;
            p.kind = "coin";
            p.rho_s = node["rho_s"].as<double>(2700.0);
            p.L = node["L"].as<double>(0.024);
            p.h = node["h"].as<double>(0.0018);
            if (node["role"]) p.label = node["role"].as<std::string>();
            if (node["notes"]) p.source = node["notes"].as<std::string>();
            p.enabled = true;

            plates.push_back(p);
        }
    } catch (const std::exception& e) {
        std::cerr << "[Config] Failed to load " << filepath << ": " << e.what() << std::endl;
    }
    return plates;
}

std::vector<PlateConfig> load_coins_yaml(const std::string& filepath) {
    std::vector<PlateConfig> plates;
    try {
        YAML::Node root = YAML::LoadFile(filepath);
        if (root["coins"]) {
            for (const auto& item : root["coins"]) {
                PlateConfig p;
                p.id = item["id"].as<std::string>("");
                p.label = item["label"].as<std::string>(p.id);
                p.kind = item["kind"].as<std::string>("coin");

                // If washer, ignore for this version (Section 7.1)
                if (p.kind == "washer") {
                    std::cout << "[Config] Skipping washer entry '" << p.id << "' (feature planned for later version)\n";
                    continue;
                }

                if (item["mass_g"]) {
                    p.mass_g = item["mass_g"].as<double>(0.0);
                }

                if (item["rho_s_kgm3"]) {
                    p.rho_s = item["rho_s_kgm3"].as<double>(p.rho_s);
                }

                if (item["diameter_mm"]) {
                    p.L = item["diameter_mm"].as<double>(25.0) * 1e-3;
                }

                if (item["thickness_mm"] && !item["thickness_mm"].IsNull()) {
                    p.h = item["thickness_mm"].as<double>() * 1e-3;
                } else {
                    p.h = 0.0;
                    p.enabled = false; // missing thickness disables entry
                }

                if (item["material"]) {
                    p.material = item["material"].as<std::string>("brass");
                }

                if (item["enabled"]) {
                    p.enabled = item["enabled"].as<bool>() && (p.h > 0.0);
                }

                if (item["source"]) {
                    p.source = item["source"].as<std::string>();
                }

                // Compute effective solid density from mass and cylinder volume, or mass from density
                if (p.mass_g > 0.0 && p.L > 0.0 && p.h > 0.0) {
                    double vol_3d = M_PI * (0.5 * p.L) * (0.5 * p.L) * p.h;
                    p.rho_s = (p.mass_g * 1e-3) / vol_3d;
                } else if (p.rho_s > 0.0 && p.L > 0.0 && p.h > 0.0) {
                    double vol_3d = M_PI * (0.5 * p.L) * (0.5 * p.L) * p.h;
                    p.mass_g = p.rho_s * vol_3d * 1e3;
                }

                plates.push_back(p);
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "[Config] Failed to load " << filepath << ": " << e.what() << std::endl;
    }
    return plates;
}

} // namespace autumn
