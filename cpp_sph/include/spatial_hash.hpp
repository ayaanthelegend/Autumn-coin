#pragma once

#include "config.hpp"
#include <vector>
#include <cstdint>
#include <cmath>
#include <algorithm>

namespace sph {

class SpatialHash {
public:
    double cell_size = 0.0026;
    double inv_cell_size = 1.0 / 0.0026;
    double origin_x = -1.0;
    double origin_y = -1.0;
    int nx = 0;
    int ny = 0;

    // Flat cell array storing particle indices
    std::vector<std::vector<int>> cells;

    SpatialHash() = default;

    void init(double min_x, double max_x, double min_y, double max_y, double cutoff) {
        cell_size = cutoff;
        inv_cell_size = 1.0 / cell_size;
        // Expand slightly for safety margin
        origin_x = min_x - 2.0 * cell_size;
        origin_y = min_y - 2.0 * cell_size;
        double width = (max_x + 2.0 * cell_size) - origin_x;
        double height = (max_y + 2.0 * cell_size) - origin_y;
        nx = static_cast<int>(std::ceil(width * inv_cell_size)) + 1;
        ny = static_cast<int>(std::ceil(height * inv_cell_size)) + 1;
        cells.assign(nx * ny, {});
    }

    void clear() {
        for (auto& c : cells) {
            c.clear();
        }
    }

    inline int get_cell_index(double x, double y) const {
        int cx = static_cast<int>(std::floor((x - origin_x) * inv_cell_size));
        int cy = static_cast<int>(std::floor((y - origin_y) * inv_cell_size));
        if (cx < 0) cx = 0;
        if (cx >= nx) cx = nx - 1;
        if (cy < 0) cy = 0;
        if (cy >= ny) cy = ny - 1;
        return cy * nx + cx;
    }

    inline void insert(int particle_idx, double x, double y) {
        int idx = get_cell_index(x, y);
        cells[idx].push_back(particle_idx);
    }

    template<typename Callback>
    inline void query_neighbors(double x, double y, double r_cutoff, Callback&& cb) const {
        double r_sq = r_cutoff * r_cutoff;
        int cx = static_cast<int>(std::floor((x - origin_x) * inv_cell_size));
        int cy = static_cast<int>(std::floor((y - origin_y) * inv_cell_size));

        int min_cx = std::max(0, cx - 1);
        int max_cx = std::min(nx - 1, cx + 1);
        int min_cy = std::max(0, cy - 1);
        int max_cy = std::min(ny - 1, cy + 1);

        for (int j_cy = min_cy; j_cy <= max_cy; ++j_cy) {
            int row_offset = j_cy * nx;
            for (int j_cx = min_cx; j_cx <= max_cx; ++j_cx) {
                const auto& cell_particles = cells[row_offset + j_cx];
                for (int p_idx : cell_particles) {
                    cb(p_idx);
                }
            }
        }
    }
};

} // namespace sph
