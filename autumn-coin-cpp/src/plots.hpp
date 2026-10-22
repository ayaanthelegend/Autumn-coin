#pragma once

#include "autumn/types.hpp"
#include <vector>
#include <string>

namespace autumn {

struct ScrollBuf {
    int max = 25000;
    int off = 0;
    std::vector<float> x;
    std::vector<float> y;

    void clear() {
        x.clear();
        y.clear();
        off = 0;
    }

    void add(float xv, float yv) {
        if ((int)x.size() < max) {
            x.push_back(xv);
            y.push_back(yv);
        } else {
            x[off] = xv;
            y[off] = yv;
            off = (off + 1) % max;
        }
    }

    int size() const { return (int)x.size(); }
    bool empty() const { return x.empty(); }
};

struct PlotData {
    ScrollBuf traj_xy;   // X [cm] vs Y [cm]
    ScrollBuf theta;     // t [s] vs theta [deg]
    ScrollBuf omega;     // t [s] vs omega [rad/s]
    ScrollBuf speed_y;   // t [s] vs vertical speed -vy [cm/s]
    ScrollBuf speed_x;   // t [s] vs horizontal vx [cm/s]
    ScrollBuf depth;     // t [s] vs depth -Y [cm]
    ScrollBuf phase;     // theta mod 2pi [rad] vs omega [rad/s]
    ScrollBuf alpha;     // t [s] vs alpha [deg]

    bool compare_previous = false;
    std::vector<std::vector<Vec2>> previous_runs; // Previous trajectories in cm

    void clear() {
        traj_xy.clear();
        theta.clear();
        omega.clear();
        speed_y.clear();
        speed_x.clear();
        depth.clear();
        phase.clear();
        alpha.clear();
    }

    void add_sample(const Sample& s);
    void archive_run(const std::vector<Sample>& samples);
};

class LivePlotPanel {
public:
    LivePlotPanel();

    void render(PlotData& data, float width, float height);

private:
    void setup_light_style();
    bool style_initialized_ = false;
};

} // namespace autumn
