#include "config.hpp"
#include "kernels.hpp"
#include "sph_solver.hpp"
#include "validation_tests.hpp"
#include "software_renderer.hpp"
#include "ode_replay.hpp"
#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <iomanip>
#include <filesystem>

using namespace sph;

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cout << "Autumn Coin: C++20 2D WCSPH-FSI Solver & Sebastian Lague-Style Renderer\n"
                  << "Usage:\n"
                  << "  sph_runner --all-tests\n"
                  << "  sph_runner --test <1..7>\n"
                  << "  sph_runner --fsi-drop [options]\n"
                  << "  sph_runner --ode-replay <trajectory.csv> <out_dir> [options]\n";
        return 0;
    }

    std::string mode = argv[1];

    if (mode == "--all-tests") {
        run_all_validation_tests();
        return 0;
    }

    if (mode == "--test") {
        if (argc < 3) {
            std::cerr << "Error: --test requires test number (1..7)\n";
            return 1;
        }
        int tnum = std::stoi(argv[2]);
        TestReport rep;
        switch (tnum) {
            case 1: rep = run_test_1(); break;
            case 2: rep = run_test_2(); break;
            case 3: rep = run_test_3(); break;
            case 4: rep = run_test_4(); break;
            case 5: rep = run_test_5(); break;
            case 6: rep = run_test_6(); break;
            case 7: rep = run_test_7(); break;
            default:
                std::cerr << "Invalid test number: " << tnum << "\n";
                return 1;
        }
        std::cout << "[TEST " << rep.test_number << "] " << rep.test_name << "\n";
        std::cout << "  Status: " << (rep.passed ? "PASSED" : "FAILED") << "\n";
        std::cout << "  Metrics: " << rep.summary_metrics << "\n";
        std::cout << "  Output: " << rep.csv_path << "\n";
        return rep.passed ? 0 : 1;
    }

    if (mode == "--ode-replay") {
        if (argc < 4) {
            std::cerr << "Usage: sph_runner --ode-replay <csv_file> <out_dir>\n";
            return 1;
        }
        std::string csv_file = argv[2];
        std::string out_dir = argv[3];
        bool ok = run_ode_replay(csv_file, out_dir);
        return ok ? 0 : 1;
    }

    if (mode == "--fsi-drop") {
        // Defaults
        double I_star = 0.68;
        double L = 0.024;
        double h = 0.0018;
        double mu = 0.001;
        double rho_f = 998.0;
        double theta0_deg = 5.0;
        double t_end = 1.0;
        double dt = 5e-5;
        double dx = 0.0012;
        std::string out_csv = "results_sph/drops/trajectory.csv";
        bool do_render = false;
        std::string render_dir = "results_sph/drops/frames";
        std::string render_mode = "speed";
        int render_stride = 50;

        for (int i = 2; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--Istar" && i + 1 < argc) I_star = std::stod(argv[++i]);
            else if (arg == "--L" && i + 1 < argc) L = std::stod(argv[++i]);
            else if (arg == "--h" && i + 1 < argc) h = std::stod(argv[++i]);
            else if (arg == "--mu" && i + 1 < argc) mu = std::stod(argv[++i]);
            else if (arg == "--rho_f" && i + 1 < argc) rho_f = std::stod(argv[++i]);
            else if (arg == "--theta0" && i + 1 < argc) theta0_deg = std::stod(argv[++i]);
            else if (arg == "--t_end" && i + 1 < argc) t_end = std::stod(argv[++i]);
            else if (arg == "--dt" && i + 1 < argc) dt = std::stod(argv[++i]);
            else if (arg == "--dx" && i + 1 < argc) dx = std::stod(argv[++i]);
            else if (arg == "--out-csv" && i + 1 < argc) out_csv = argv[++i];
            else if (arg == "--render") do_render = true;
            else if (arg == "--render-dir" && i + 1 < argc) render_dir = argv[++i];
            else if (arg == "--render-mode" && i + 1 < argc) render_mode = argv[++i];
            else if (arg == "--render-stride" && i + 1 < argc) render_stride = std::stoi(argv[++i]);
        }

        // rho_s from I_star = (rho_s * h) / (rho_f * L)
        double rho_s = (I_star * rho_f * L) / h;

        FluidConfig f_cfg;
        f_cfg.rho0 = rho_f;
        f_cfg.mu = mu;
        f_cfg.gravity = {0.0, -9.81};
        f_cfg.c0 = 25.0;

        SPHConfig s_cfg;
        s_cfg.dx = dx;
        s_cfg.h_factor = 1.3;
        s_cfg.alpha_art = 0.0;
        s_cfg.dt = dt;
        s_cfg.t_end = t_end;

        // Tank sizing: W_tank >= 12 L
        double W_tank = std::max(0.20, 12.0 * L);
        double H_tank = 0.35;

        DomainConfig d_cfg;
        d_cfg.x_min = -W_tank * 0.5;
        d_cfg.x_max = W_tank * 0.5;
        d_cfg.y_min = -H_tank;
        d_cfg.y_max = 0.02;

        RigidPlateConfig p_cfg;
        p_cfg.L = L;
        p_cfg.h = h;
        p_cfg.rho_s = rho_s;
        p_cfg.pos = {0.0, -0.04};
        p_cfg.theta = theta0_deg * M_PI / 180.0;
        p_cfg.fixed = true; // Hold fixed during equilibration to prevent start-up shock

        SPHSolver solver(f_cfg, s_cfg, d_cfg);
        // Add rigid plate first so fluid is carved out cleanly
        solver.add_rigid_ellipse(p_cfg);
        solver.init_domain_walls();
        solver.add_fluid_block(d_cfg.x_min + 0.005, d_cfg.x_max - 0.005, d_cfg.y_min + 0.005, 0.0, dx);

        // Fluid-structure equilibration: hold plate fixed to relax acoustic pressure transients
        int equil_steps = 100;
        EquilibrationResult eq_rep = solver.equilibrate(equil_steps, dt);
        std::cout << "[FSI Drop] Equilibration complete (" << equil_steps << " steps):\n"
                  << "  Initial a_y (measured): " << std::fixed << std::setprecision(3) << eq_rep.initial_ay_measured << " m/s^2\n"
                  << "  Initial a_y (theoretical added mass): " << eq_rep.initial_ay_theoretical << " m/s^2\n"
                  << "  Initial alpha: " << eq_rep.initial_alpha << " rad/s^2 (Shock suppressed: "
                  << (eq_rep.shock_suppressed ? "YES" : "NO") << ")\n";

        std::filesystem::path csv_path(out_csv);
        if (csv_path.has_parent_path()) {
            std::filesystem::create_directories(csv_path.parent_path());
        }
        std::ofstream csv(out_csv);
        csv << "t,X,Y,U,V,theta,omega,ax,ay,alpha\n";

        SoftwareRenderer renderer(960, 1280, 2200.0);
        renderer.set_view(0.0, -0.15, 2200.0);
        if (do_render) {
            std::filesystem::create_directories(render_dir);
        }

        std::cout << "[FSI Drop] Starting simulation:\n"
                  << "  I* = " << I_star << " | L = " << L << " m | h = " << h << " m\n"
                  << "  rho_s = " << rho_s << " kg/m^3 | mu = " << mu << " Pa*s\n"
                  << "  dx = " << dx << " m (N_h = " << (h / dx) << ") | dt = " << dt << " s\n"
                  << "  W_tank = " << W_tank << " m (Blockage: " << (L / W_tank * 100.0) << "%)\n";

        int total_steps = static_cast<int>(std::round(t_end / dt));
        int frame_idx = 0;

        for (int step = 0; step <= total_steps; ++step) {
            const auto& coin = solver.rigid_bodies[0];

            // Stopping criterion: 2L from bottom or walls
            if (coin.pos.y <= d_cfg.y_min + 2.0 * L ||
                std::abs(coin.pos.x) >= d_cfg.x_max - 2.0 * L) {
                std::cout << "[FSI Drop] Stopping criterion reached (2L proximity to boundary) at t = "
                          << solver.sim_time << " s\n";
                break;
            }

            if (step % 20 == 0) {
                csv << std::fixed << std::setprecision(6)
                    << solver.sim_time << "," << coin.pos.x << "," << coin.pos.y << ","
                    << coin.vel.x << "," << coin.vel.y << "," << coin.theta << ","
                    << coin.omega << "," << coin.acc.x << "," << coin.acc.y << ","
                    << coin.alpha << "\n";
            }

            if (do_render && (step % render_stride == 0)) {
                renderer.render_sph_frame(solver, "2D SPH-FSI numerical simulation", render_mode,
                                          (render_mode == "vorticity" ? 40.0 : 0.35));
                std::ostringstream fn;
                fn << render_dir << "/frame_" << std::setfill('0') << std::setw(4) << frame_idx++ << ".png";
                renderer.save_png(fn.str());
            }

            solver.step_kdk(dt);
        }
        csv.close();
        std::cout << "[FSI Drop] Completed. Trajectory saved to " << out_csv << "\n";
        return 0;
    }

    std::cerr << "Unknown mode: " << mode << "\n";
    return 1;
}
