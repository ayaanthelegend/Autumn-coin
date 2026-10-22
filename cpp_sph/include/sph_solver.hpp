#pragma once

#include "config.hpp"
#include "fluid_state.hpp"
#include "rigid_ellipse.hpp"
#include "kernels.hpp"
#include "spatial_hash.hpp"
#include <vector>
#include <memory>
#include <string>

namespace sph {

class SPHSolver {
public:
    FluidConfig fluid_cfg;
    SPHConfig sph_cfg;
    DomainConfig domain_cfg;
    WendlandC2Kernel kernel;

    std::vector<FluidParticle> fluid_particles;
    std::vector<BoundaryParticle> wall_particles;
    std::vector<RigidEllipse> rigid_bodies;

    SpatialHash fluid_hash;
    SpatialHash boundary_hash;

    // Helper vector combining all boundary particles for neighbor search
    std::vector<BoundaryParticle*> all_boundary_ptrs;

    double sim_time = 0.0;
    int step_count = 0;

    SPHSolver() = default;
    SPHSolver(const FluidConfig& f_cfg, const SPHConfig& s_cfg, const DomainConfig& d_cfg);

    void init_domain_walls();
    void build_neighbor_lists();
    void compute_densities_and_pressures();
    void extrapolate_boundary_pressures();
    void compute_accelerations_and_fsi(Vec2& out_plate_force, double& out_plate_torque);
    void compute_vorticity();

    // Synchronous Kick-Drift-Kick (KDK) step
    void step_kdk(double dt);

    // Helpers
    bool is_inside_solid(double x, double y) const;
    void add_fluid_block(double x_min, double x_max, double y_min, double y_max, double dx);
    void add_rigid_ellipse(const RigidPlateConfig& plate_cfg);

    // Periodic distance wrapping
    Vec2 wrap_displacement(const Vec2& dr) const;
    void wrap_position(Vec2& pos) const;
};

} // namespace sph
