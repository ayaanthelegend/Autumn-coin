#pragma once

#include "config.hpp"
#include "software_renderer.hpp"
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <iostream>
#include <filesystem>
#include <iomanip>

namespace sph {

struct ODEReplayPoint {
    double t = 0.0;
    double X = 0.0;
    double Y = 0.0;
    double U = 0.0;
    double V = 0.0;
    double theta = 0.0;
    double omega = 0.0;
};

inline bool run_ode_replay(const std::string& csv_path,
                           const std::string& out_dir,
                           double L = 0.024,
                           double h = 0.0018,
                           double I_star = 0.68,
                           double Re_meas = 850.0,
                           const std::string& regime_label = "Fluttering",
                           int frame_stride = 10) {
    std::ifstream file(csv_path);
    if (!file.is_open()) {
        std::cerr << "[ODE Replay] Could not open file: " << csv_path << "\n";
        return false;
    }

    std::filesystem::create_directories(out_dir);

    std::string line;
    // Read header
    if (!std::getline(file, line)) return false;

    // Parse header to find column indices
    std::stringstream ss(line);
    std::string col;
    int idx = 0;
    int col_t = -1, col_X = -1, col_Y = -1, col_U = -1, col_V = -1, col_th = -1, col_om = -1;

    while (std::getline(ss, col, ',')) {
        // Trim whitespace
        col.erase(0, col.find_first_not_of(" \t\r\n"));
        col.erase(col.find_last_not_of(" \t\r\n") + 1);

        if (col == "t") col_t = idx;
        else if (col == "X" || col == "x") col_X = idx;
        else if (col == "Y" || col == "y") col_Y = idx;
        else if (col == "U" || col == "u" || col == "vx") col_U = idx;
        else if (col == "V" || col == "v" || col == "vy") col_V = idx;
        else if (col == "theta" || col == "th") col_th = idx;
        else if (col == "omega" || col == "om") col_om = idx;
        idx++;
    }

    if (col_t == -1 || col_X == -1 || col_Y == -1 || col_th == -1) {
        // Assume default order: t, X, Y, U, V, theta, omega
        col_t = 0; col_X = 1; col_Y = 2; col_U = 3; col_V = 4; col_th = 5; col_om = 6;
    }

    std::vector<ODEReplayPoint> points;
    double min_Y = 0.0, max_Y = 0.0;
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        std::stringstream line_ss(line);
        std::string val;
        std::vector<double> row;
        while (std::getline(line_ss, val, ',')) {
            try {
                row.push_back(std::stod(val));
            } catch (...) {
                row.push_back(0.0);
            }
        }
        if (row.size() > static_cast<size_t>(std::max({col_t, col_X, col_Y, col_th}))) {
            ODEReplayPoint pt;
            pt.t = row[col_t];
            pt.X = row[col_X];
            pt.Y = row[col_Y];
            pt.theta = row[col_th];
            if (col_U >= 0 && col_U < static_cast<int>(row.size())) pt.U = row[col_U];
            if (col_V >= 0 && col_V < static_cast<int>(row.size())) pt.V = row[col_V];
            if (col_om >= 0 && col_om < static_cast<int>(row.size())) pt.omega = row[col_om];
            min_Y = std::min(min_Y, pt.Y);
            max_Y = std::max(max_Y, pt.Y);
            points.push_back(pt);
        }
    }

    std::cout << "[ODE Replay] Loaded " << points.size() << " trajectory points from " << csv_path << "\n";
    if (points.empty()) return false;

    SoftwareRenderer renderer(960, 1280, 2200.0);
    double center_y = (min_Y + max_Y) * 0.5;
    renderer.set_view(0.0, center_y, 2200.0);

    int frame_num = 0;
    for (size_t i = 0; i < points.size(); i += frame_stride) {
        const auto& pt = points[i];
        renderer.render_ode_replay_frame({pt.X, pt.Y}, pt.theta, L, h, pt.t, I_star, Re_meas, regime_label);
        
        std::ostringstream fn;
        fn << out_dir << "/frame_" << std::setfill('0') << std::setw(4) << frame_num << ".png";
        renderer.save_png(fn.str());
        frame_num++;
    }

    std::cout << "[ODE Replay] Rendered " << frame_num << " frames into " << out_dir << "\n";
    return true;
}

} // namespace sph
