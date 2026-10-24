#include "sph_solver.hpp"
#include <cmath>
#include <algorithm>
#include <iostream>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace sph {

SPHSolver::SPHSolver(const FluidConfig& f_cfg, const SPHConfig& s_cfg, const DomainConfig& d_cfg)
    : fluid_cfg(f_cfg), sph_cfg(s_cfg), domain_cfg(d_cfg), kernel(s_cfg.h_sml()) {
}

Vec2 SPHSolver::wrap_displacement(const Vec2& dr) const {
    Vec2 res = dr;
    if (domain_cfg.periodic_x) {
        double Lx = domain_cfg.x_max - domain_cfg.x_min;
        if (res.x > 0.5 * Lx) res.x -= Lx;
        else if (res.x < -0.5 * Lx) res.x += Lx;
    }
    if (domain_cfg.periodic_y) {
        double Ly = domain_cfg.y_max - domain_cfg.y_min;
        if (res.y > 0.5 * Ly) res.y -= Ly;
        else if (res.y < -0.5 * Ly) res.y += Ly;
    }
    return res;
}

void SPHSolver::wrap_position(Vec2& pos) const {
    if (domain_cfg.periodic_x) {
        double Lx = domain_cfg.x_max - domain_cfg.x_min;
        while (pos.x < domain_cfg.x_min) pos.x += Lx;
        while (pos.x >= domain_cfg.x_max) pos.x -= Lx;
    }
    if (domain_cfg.periodic_y) {
        double Ly = domain_cfg.y_max - domain_cfg.y_min;
        while (pos.y < domain_cfg.y_min) pos.y += Ly;
        while (pos.y >= domain_cfg.y_max) pos.y -= Ly;
    }
}

bool SPHSolver::is_inside_solid(double x, double y) const {
    for (const auto& rb : rigid_bodies) {
        double cos_th = std::cos(-rb.theta);
        double sin_th = std::sin(-rb.theta);
        double dx = x - rb.pos.x;
        double dy = y - rb.pos.y;
        double lx = cos_th * dx - sin_th * dy;
        double ly = sin_th * dx + cos_th * dy;
        double a = rb.config.a();
        double b = rb.config.b();
        // Buffer of 0.5 * dx to ensure no particle overlaps with boundary particles
        double scale_a = a + 0.25 * sph_cfg.dx;
        double scale_b = b + 0.25 * sph_cfg.dx;
        if ((lx * lx) / (scale_a * scale_a) + (ly * ly) / (scale_b * scale_b) <= 1.0) {
            return true;
        }
    }
    return false;
}

void SPHSolver::init_domain_walls() {
    wall_particles.clear();
    double dx = sph_cfg.dx;
    int layers = domain_cfg.boundary_layers;

    double x0 = domain_cfg.x_min;
    double x1 = domain_cfg.x_max;
    double y0 = domain_cfg.y_min;
    double y1 = domain_cfg.y_max;

    // Bottom wall
    if (!domain_cfg.periodic_y) {
        int nx_bottom = static_cast<int>(std::round((x1 - x0) / dx)) + 2 * layers;
        for (int l = 1; l <= layers; ++l) {
            double y = y0 - l * dx;
            for (int i = 0; i <= nx_bottom; ++i) {
                double x = (x0 - layers * dx) + i * dx;
                BoundaryParticle bp;
                bp.pos = {x, y};
                bp.vel = {0.0, 0.0};
                bp.vel_half = {0.0, 0.0};
                bp.acc = {0.0, 0.0};
                bp.normal = {0.0, 1.0};
                bp.psi = dx * dx;
                bp.p = 0.0;
                bp.body_id = -1;
                wall_particles.push_back(bp);
            }
        }
    }

    // Left and right walls
    if (!domain_cfg.periodic_x) {
        int ny = static_cast<int>(std::round((y1 - y0) / dx));
        for (int j = 0; j <= ny; ++j) {
            double y = y0 + j * dx;
            for (int l = 1; l <= layers; ++l) {
                BoundaryParticle bp_left;
                bp_left.pos = {x0 - l * dx, y};
                bp_left.normal = {1.0, 0.0};
                bp_left.psi = dx * dx;
                bp_left.body_id = -1;
                wall_particles.push_back(bp_left);

                BoundaryParticle bp_right;
                bp_right.pos = {x1 + l * dx, y};
                bp_right.normal = {-1.0, 0.0};
                bp_right.psi = dx * dx;
                bp_right.body_id = -1;
                wall_particles.push_back(bp_right);
            }
        }
    }

    // Compute Akinci boundary volume Psi_b = 1 / sum W_bk for wall particles
    SpatialHash wall_hash;
    double r_c = kernel.r_cutoff;
    wall_hash.init(x0 - 5.0 * dx, x1 + 5.0 * dx, y0 - 5.0 * dx, y1 + 5.0 * dx, r_c);
    for (int i = 0; i < static_cast<int>(wall_particles.size()); ++i) {
        wall_hash.insert(i, wall_particles[i].pos.x, wall_particles[i].pos.y);
    }
    for (auto& bp : wall_particles) {
        double sum_W = 0.0;
        wall_hash.query_neighbors(bp.pos.x, bp.pos.y, r_c, [&](int j) {
            double r = (bp.pos - wall_particles[j].pos).length();
            if (r < r_c) {
                sum_W += kernel.value(r);
            }
        });
        if (sum_W > 1e-6) {
            bp.psi = 1.0 / sum_W;
        } else {
            bp.psi = dx * dx;
        }
    }
}

void SPHSolver::add_fluid_block(double x_min, double x_max, double y_min, double y_max, double dx) {
    double m0 = fluid_cfg.rho0 * dx * dx;
    int nx = static_cast<int>(std::round((x_max - x_min) / dx));
    int ny = static_cast<int>(std::round((y_max - y_min) / dx));

    for (int j = 0; j <= ny; ++j) {
        double y = y_min + j * dx;
        for (int i = 0; i <= nx; ++i) {
            double x = x_min + i * dx;

            // Check if point is inside any solid obstacle/plate
            if (is_inside_solid(x, y)) {
                continue;
            }

            FluidParticle p;
            p.pos = {x, y};
            p.vel = {0.0, 0.0};
            p.vel_half = {0.0, 0.0};
            p.acc = {0.0, 0.0};
            p.rho = fluid_cfg.rho0;
            p.p = 0.0;
            p.mass = m0;
            p.volume = dx * dx;
            p.vorticity = 0.0;
            fluid_particles.push_back(p);
        }
    }
}

void SPHSolver::add_rigid_ellipse(const RigidPlateConfig& plate_cfg) {
    int id = static_cast<int>(rigid_bodies.size());
    RigidEllipse re(plate_cfg, id);
    re.init_discretization(sph_cfg.dx, kernel);
    rigid_bodies.push_back(re);
}

void SPHSolver::build_neighbor_lists() {
    double r_c = kernel.r_cutoff;

    all_boundary_ptrs.clear();
    for (auto& bp : wall_particles) {
        all_boundary_ptrs.push_back(&bp);
    }
    for (auto& rb : rigid_bodies) {
        for (auto& bp : rb.particles) {
            all_boundary_ptrs.push_back(&bp);
        }
    }

    double min_x = domain_cfg.x_min - 6.0 * sph_cfg.dx;
    double max_x = domain_cfg.x_max + 6.0 * sph_cfg.dx;
    double min_y = domain_cfg.y_min - 6.0 * sph_cfg.dx;
    double max_y = domain_cfg.y_max + 6.0 * sph_cfg.dx;

    for (const auto& p : fluid_particles) {
        min_x = std::min(min_x, p.pos.x);
        max_x = std::max(max_x, p.pos.x);
        min_y = std::min(min_y, p.pos.y);
        max_y = std::max(max_y, p.pos.y);
    }
    for (const auto* bp : all_boundary_ptrs) {
        min_x = std::min(min_x, bp->pos.x);
        max_x = std::max(max_x, bp->pos.x);
        min_y = std::min(min_y, bp->pos.y);
        max_y = std::max(max_y, bp->pos.y);
    }

    fluid_hash.init(min_x, max_x, min_y, max_y, r_c);
    boundary_hash.init(min_x, max_x, min_y, max_y, r_c);

    for (int i = 0; i < static_cast<int>(fluid_particles.size()); ++i) {
        fluid_hash.insert(i, fluid_particles[i].pos.x, fluid_particles[i].pos.y);
    }
    for (int b = 0; b < static_cast<int>(all_boundary_ptrs.size()); ++b) {
        boundary_hash.insert(b, all_boundary_ptrs[b]->pos.x, all_boundary_ptrs[b]->pos.y);
    }
}

void SPHSolver::compute_densities_and_pressures() {
    double r_c = kernel.r_cutoff;
    double rho0 = fluid_cfg.rho0;
    double c0 = fluid_cfg.c0;
    double gamma = fluid_cfg.gamma;
    double p_bg = fluid_cfg.p_bg;
    double B = (rho0 * c0 * c0) / gamma;

    int n_fluid = static_cast<int>(fluid_particles.size());

    #pragma omp parallel for schedule(dynamic, 64)
    for (int i = 0; i < n_fluid; ++i) {
        auto& pi = fluid_particles[i];
        double density_num = 0.0;
        double density_den = 0.0;

        // Sum over fluid neighbors
        fluid_hash.query_neighbors(pi.pos.x, pi.pos.y, r_c, [&](int j) {
            Vec2 rij = wrap_displacement(pi.pos - fluid_particles[j].pos);
            double r = rij.length();
            if (r < r_c) {
                double W = kernel.value(r);
                density_num += fluid_particles[j].mass * W;
                density_den += (fluid_particles[j].mass / fluid_particles[j].rho) * W;
            }
        });

        // Sum over boundary neighbors (Akinci et al. 2012)
        boundary_hash.query_neighbors(pi.pos.x, pi.pos.y, r_c, [&](int b) {
            const auto* bp = all_boundary_ptrs[b];
            Vec2 rib = wrap_displacement(pi.pos - bp->pos);
            double r = rib.length();
            if (r < r_c) {
                double W = kernel.value(r);
                density_num += rho0 * bp->psi * W;
                density_den += bp->psi * W;
            }
        });

        if (sph_cfg.use_shepard_density && density_den > 1e-6) {
            pi.rho = std::max(density_num / density_den, 0.5 * rho0);
        } else {
            pi.rho = std::max(density_num, 0.5 * rho0);
        }

        // Tait Equation of State
        if (!sph_cfg.compute_pressure) {
            pi.p = 0.0;
        } else {
            double density_ratio = pi.rho / rho0;
            double p = B * (std::pow(density_ratio, gamma) - 1.0) + p_bg;
            pi.p = std::max(p, 0.0);
        }
    }
}

void SPHSolver::extrapolate_boundary_pressures() {
    double r_c = kernel.r_cutoff;
    double rho0 = fluid_cfg.rho0;
    Vec2 g = fluid_cfg.gravity;
    int n_boundary = static_cast<int>(all_boundary_ptrs.size());

    #pragma omp parallel for schedule(dynamic, 64)
    for (int b = 0; b < n_boundary; ++b) {
        auto* bp = all_boundary_ptrs[b];
        double sum_p_W = 0.0;
        double sum_W = 0.0;

        Vec2 a_b = bp->acc;
        Vec2 g_minus_a = g - a_b;

        fluid_hash.query_neighbors(bp->pos.x, bp->pos.y, r_c, [&](int i) {
            const auto& pi = fluid_particles[i];
            Vec2 r_bi = wrap_displacement(bp->pos - pi.pos);
            double r = r_bi.length();
            if (r < r_c) {
                double W = kernel.value(r);
                double p_hydro = rho0 * g_minus_a.dot(r_bi);
                sum_p_W += (pi.p + p_hydro) * W;
                sum_W += W;
            }
        });

        if (sum_W > 1e-6) {
            bp->p = std::max(0.0, sum_p_W / sum_W);
        } else {
            bp->p = 0.0;
        }
    }
}

void SPHSolver::compute_accelerations_and_fsi(Vec2& out_plate_force, double& out_plate_torque) {
    double r_c = kernel.r_cutoff;
    double rho0 = fluid_cfg.rho0;
    double nu = fluid_cfg.nu();
    double alpha_art = sph_cfg.alpha_art;
    double c0 = fluid_cfg.c0;
    double h = kernel.h;
    double h_sq = h * h;
    Vec2 g = fluid_cfg.gravity;

    int n_fluid = static_cast<int>(fluid_particles.size());
    int n_boundary = static_cast<int>(all_boundary_ptrs.size());

    for (int i = 0; i < n_fluid; ++i) {
        fluid_particles[i].acc = g;
    }

    std::vector<Vec2> f_boundary(n_boundary, Vec2{0.0, 0.0});

    #pragma omp parallel
    {
        std::vector<Vec2> local_f_boundary(n_boundary, Vec2{0.0, 0.0});

        #pragma omp for schedule(dynamic, 64)
        for (int i = 0; i < n_fluid; ++i) {
            auto& pi = fluid_particles[i];
            double p_i_rho_sq = pi.p / (pi.rho * pi.rho);
            Vec2 a_fluid{0.0, 0.0};

            // Fluid-fluid interaction
            fluid_hash.query_neighbors(pi.pos.x, pi.pos.y, r_c, [&](int j) {
                if (i == j) return;
                const auto& pj = fluid_particles[j];
                Vec2 rij = wrap_displacement(pi.pos - pj.pos);
                double r = rij.length();
                if (r < r_c && r > 1e-12) {
                    Vec2 gradW = kernel.gradient(rij, r);
                    double p_j_rho_sq = pj.p / (pj.rho * pj.rho);

                    double Pi_ij = 0.0;
                    if (alpha_art > 0.0) {
                        Vec2 vij = pi.vel - pj.vel;
                        double vr = vij.dot(rij);
                        if (vr < 0.0) {
                            double mu_ij = (h * vr) / (r * r + 0.01 * h_sq);
                            double rho_bar = 0.5 * (pi.rho + pj.rho);
                            Pi_ij = -alpha_art * c0 * mu_ij / rho_bar;
                        }
                    }

                    // Pressure gradient acceleration
                    Vec2 f_p = -gradW * (pj.mass * (p_i_rho_sq + p_j_rho_sq + Pi_ij));
                    a_fluid += f_p;

                    // Physical Morris laminar viscosity
                    Vec2 vij = pi.vel - pj.vel;
                    double dot_prod = rij.dot(gradW);
                    double visc_coeff = 2.0 * nu * (pj.mass / pj.rho) * (dot_prod / (r * r + 0.01 * h_sq));
                    a_fluid += vij * visc_coeff;
                }
            });

            // Fluid-boundary interaction (Akinci et al. 2012)
            boundary_hash.query_neighbors(pi.pos.x, pi.pos.y, r_c, [&](int b) {
                const auto* bp = all_boundary_ptrs[b];
                Vec2 rib = wrap_displacement(pi.pos - bp->pos);
                double r = rib.length();
                if (r < r_c && r > 1e-12) {
                    Vec2 gradW = kernel.gradient(rib, r);
                    double p_b_rho_sq = bp->p / (rho0 * rho0);

                    double Pi_ib = 0.0;
                    if (alpha_art > 0.0) {
                        Vec2 vib = pi.vel - bp->vel;
                        double vr = vib.dot(rib);
                        if (vr < 0.0) {
                            double mu_ib = (h * vr) / (r * r + 0.01 * h_sq);
                            Pi_ib = -alpha_art * c0 * mu_ib / rho0;
                        }
                    }

                    // Pressure force from boundary on fluid particle i
                    Vec2 f_p_ib = -gradW * (pi.mass * rho0 * bp->psi * (p_i_rho_sq + p_b_rho_sq + Pi_ib));

                    // Viscous force from boundary on fluid particle i
                    Vec2 vib = pi.vel - bp->vel;
                    double dot_prod = rib.dot(gradW);
                    double visc_coeff = 2.0 * nu * pi.mass * bp->psi * (dot_prod / (r * r + 0.01 * h_sq));
                    Vec2 f_v_ib = vib * visc_coeff;

                    Vec2 total_f_ib = f_p_ib + f_v_ib;

                    // Acceleration of fluid particle i
                    a_fluid += total_f_ib / pi.mass;

                    // Reaction force on boundary particle: -f_ib
                    local_f_boundary[b] -= total_f_ib;
                }
            });

            pi.acc += a_fluid;
        }

        #pragma omp critical
        {
            for (int b = 0; b < n_boundary; ++b) {
                f_boundary[b] += local_f_boundary[b];
            }
        }
    }

    out_plate_force = {0.0, 0.0};
    out_plate_torque = 0.0;

    for (auto& rb : rigid_bodies) {
        Vec2 rb_force{0.0, 0.0};
        double rb_torque = 0.0;

        for (int b = 0; b < n_boundary; ++b) {
            if (all_boundary_ptrs[b]->body_id == rb.body_id) {
                Vec2 f_b = f_boundary[b];
                rb_force += f_b;
                Vec2 r_arm = all_boundary_ptrs[b]->pos - rb.pos;
                rb_torque += r_arm.cross(f_b);
            }
        }

        rb.apply_force_and_torque(rb_force, rb_torque, fluid_cfg.gravity);
        out_plate_force = rb_force;
        out_plate_torque = rb_torque;
    }
}

void SPHSolver::compute_vorticity() {
    double r_c = kernel.r_cutoff;
    int n_fluid = static_cast<int>(fluid_particles.size());

    #pragma omp parallel for schedule(dynamic, 64)
    for (int i = 0; i < n_fluid; ++i) {
        auto& pi = fluid_particles[i];
        double omega_z = 0.0;

        fluid_hash.query_neighbors(pi.pos.x, pi.pos.y, r_c, [&](int j) {
            if (i == j) return;
            const auto& pj = fluid_particles[j];
            Vec2 rij = wrap_displacement(pi.pos - pj.pos);
            double r = rij.length();
            if (r < r_c && r > 1e-12) {
                Vec2 gradW = kernel.gradient(rij, r);
                double vy_diff = pj.vel.y - pi.vel.y;
                double vx_diff = pj.vel.x - pi.vel.x;
                double vol_j = pj.mass / pj.rho;
                omega_z += vol_j * (vy_diff * gradW.x - vx_diff * gradW.y);
            }
        });

        pi.vorticity = omega_z;
    }
}

void SPHSolver::step_kdk(double dt) {
    double dt_half = 0.5 * dt;
    int n_fluid = static_cast<int>(fluid_particles.size());

    // 1. First Half-Kick (t^n -> t^{n+1/2})
    #pragma omp parallel for
    for (int i = 0; i < n_fluid; ++i) {
        fluid_particles[i].vel_half = fluid_particles[i].vel + fluid_particles[i].acc * dt_half;
    }
    for (auto& rb : rigid_bodies) {
        if (!rb.config.fixed) {
            rb.vel_half = rb.vel + rb.acc * dt_half;
            rb.omega_half = rb.omega + rb.alpha * dt_half;
        }
    }

    // 2. Drift (t^n -> t^{n+1})
    #pragma omp parallel for
    for (int i = 0; i < n_fluid; ++i) {
        fluid_particles[i].pos += fluid_particles[i].vel_half * dt;
        wrap_position(fluid_particles[i].pos);
    }
    for (auto& rb : rigid_bodies) {
        if (!rb.config.fixed) {
            rb.pos += rb.vel_half * dt;
            rb.theta += rb.omega_half * dt;
            wrap_position(rb.pos);
        }
        rb.update_particles(false);
    }

    // 3. Force Evaluation at t^{n+1}
    build_neighbor_lists();
    compute_densities_and_pressures();

    int iters = sph_cfg.picard_iters;
    double omega_relax = sph_cfg.omega_relax;

    Vec2 plate_f;
    double plate_t;

    for (int iter = 0; iter < iters; ++iter) {
        extrapolate_boundary_pressures();
        compute_accelerations_and_fsi(plate_f, plate_t);

        if (iter + 1 < iters) {
            for (auto& rb : rigid_bodies) {
                if (!rb.config.fixed) {
                    rb.acc = rb.acc_prev * (1.0 - omega_relax) + rb.acc * omega_relax;
                    rb.alpha = rb.alpha_prev * (1.0 - omega_relax) + rb.alpha * omega_relax;
                    rb.update_particles(true);
                }
            }
        }
    }

    // 4. Second Half-Kick (t^{n+1/2} -> t^{n+1})
    #pragma omp parallel for
    for (int i = 0; i < n_fluid; ++i) {
        fluid_particles[i].vel = fluid_particles[i].vel_half + fluid_particles[i].acc * dt_half;
    }
    for (auto& rb : rigid_bodies) {
        if (!rb.config.fixed) {
            rb.vel = rb.vel_half + rb.acc * dt_half;
            rb.omega = rb.omega_half + rb.alpha * dt_half;
        }
        rb.update_particles(true);
    }

    if (sph_cfg.compute_vorticity) {
        compute_vorticity();
    }

    sim_time += dt;
    step_count++;
}

EquilibrationResult SPHSolver::equilibrate(int n_steps, double dt) {
    EquilibrationResult res;
    if (rigid_bodies.empty()) return res;

    auto& rb = rigid_bodies[0];
    rb.config.fixed = true;
    rb.vel = {0.0, 0.0};
    rb.vel_half = {0.0, 0.0};
    rb.omega = 0.0;
    rb.omega_half = 0.0;
    rb.acc = {0.0, 0.0};
    rb.alpha = 0.0;

    for (int s = 0; s < n_steps; ++s) {
        step_kdk(dt);
    }

    // Release plate into free flight at t = 0
    rb.config.fixed = false;
    rb.vel = {0.0, 0.0};
    rb.vel_half = {0.0, 0.0};
    rb.omega = 0.0;
    rb.omega_half = 0.0;
    sim_time = 0.0;
    step_count = 0;

    // Evaluate acceleration upon release
    Vec2 f_plate; double t_plate;
    extrapolate_boundary_pressures();
    compute_accelerations_and_fsi(f_plate, t_plate);

    res.initial_ay_measured = rb.acc.y;
    res.initial_alpha = rb.alpha;

    // Theoretical added-mass acceleration for an ellipse broadside to vertical acceleration:
    // a_0 = - (rho_s - rho_f) / (rho_s + rho_f * (L/h)) * g
    double rho_s = rb.config.rho_s;
    double rho_f = fluid_cfg.rho0;
    double L = rb.config.L;
    double h = rb.config.h;
    double g = std::abs(fluid_cfg.gravity.y);
    double m_added_ratio = (h > 1e-12) ? (L / h) : 1.0;
    double a0_theory = -((rho_s - rho_f) / (rho_s + rho_f * m_added_ratio)) * g;

    res.initial_ay_theoretical = a0_theory;
    if (std::abs(a0_theory) > 1e-6) {
        res.rel_error = std::abs(res.initial_ay_measured - a0_theory) / std::abs(a0_theory);
    }
    // Check that acoustic shock is suppressed: initial acceleration within reasonable bounds
    // of theoretical (e.g. not -190 m/s^2) and initial angular acceleration is not violent (< 50 rad/s^2)
    res.shock_suppressed = (std::abs(res.initial_ay_measured) < 2.0 * g) && 
                           (std::abs(res.initial_alpha) < 50.0);
    return res;
}

} // namespace sph
