#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr int Q = 27;
constexpr double PI = 3.141592653589793238462643383279502884;

struct Vec3 {
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;
};

struct Lattice {
    std::array<int, Q> ex{};
    std::array<int, Q> ey{};
    std::array<int, Q> ez{};
    std::array<double, Q> w{};
    std::array<int, Q> opp{};
};

struct PhaseParams {
    double phi_l = 0.0;
    double phi_h = 1.0;
    double sigma = 1.0;
    double int_width = 4.0;
};

struct ScalarMetrics {
    double max_abs = 0.0;
    double sum_abs = 0.0;
    double sum_sq = 0.0;
    int n = 0;

    void add(double v) {
        const double a = std::fabs(v);
        if (a > max_abs) max_abs = a;
        sum_abs += a;
        sum_sq += v * v;
        ++n;
    }

    double mean_abs() const {
        return n > 0 ? sum_abs / static_cast<double>(n) : 0.0;
    }

    double rms() const {
        return n > 0 ? std::sqrt(sum_sq / static_cast<double>(n)) : 0.0;
    }
};

Lattice make_d3q27_tclb_order() {
    Lattice lat;
    lat.ex = {0, 1,-1, 0, 0, 0, 0, 1,-1, 1,-1, 1,-1, 1,-1, 1,-1, 1,-1, 1,-1, 1,-1, 0, 0, 0, 0};
    lat.ey = {0, 0, 0, 1,-1, 0, 0, 1, 1,-1,-1, 1, 1,-1,-1, 1, 1,-1,-1, 0, 0, 0, 0, 1,-1, 1,-1};
    lat.ez = {0, 0, 0, 0, 0, 1,-1, 1, 1, 1, 1,-1,-1,-1,-1, 0, 0, 0, 0, 1, 1,-1,-1, 1, 1,-1,-1};
    for (int i = 0; i < Q; ++i) {
        const int nnz = (lat.ex[i] != 0) + (lat.ey[i] != 0) + (lat.ez[i] != 0);
        if (nnz == 0) lat.w[i] = 8.0 / 27.0;
        else if (nnz == 1) lat.w[i] = 2.0 / 27.0;
        else if (nnz == 2) lat.w[i] = 1.0 / 54.0;
        else lat.w[i] = 1.0 / 216.0;
    }
    for (int i = 0; i < Q; ++i) {
        lat.opp[i] = -1;
        for (int j = 0; j < Q; ++j) {
            if (lat.ex[j] == -lat.ex[i] && lat.ey[j] == -lat.ey[i] && lat.ez[j] == -lat.ez[i]) {
                lat.opp[i] = j;
                break;
            }
        }
    }
    return lat;
}

struct Grid {
    int nx = 0;
    int ny = 0;
    int nz = 0;
    std::vector<double> phi;
    std::vector<double> wall_ghost;
    std::vector<int> solid;

    Grid(int nx_, int ny_, int nz_)
        : nx(nx_), ny(ny_), nz(nz_),
          phi(static_cast<std::size_t>(nx_) * ny_ * nz_, 0.0),
          wall_ghost(static_cast<std::size_t>(nx_) * ny_ * nz_, std::numeric_limits<double>::quiet_NaN()),
          solid(static_cast<std::size_t>(nx_) * ny_ * nz_, 0) {}

    std::size_t id(int i, int j, int k) const {
        return static_cast<std::size_t>((k * ny + j) * nx + i);
    }

    bool inside(int i, int j, int k) const {
        return i >= 0 && i < nx && j >= 0 && j < ny && k >= 0 && k < nz;
    }

    double raw_phi(int i, int j, int k) const {
        return phi[id(i, j, k)];
    }

    double stencil_phi(int i, int j, int k, double fallback) const {
        if (!inside(i, j, k)) return fallback;
        const std::size_t p = id(i, j, k);
        if (solid[p] != 0) {
            const double g = wall_ghost[p];
            return std::isfinite(g) ? g : fallback;
        }
        const double v = phi[p];
        return std::isfinite(v) ? v : fallback;
    }
};

double grad_component_x(const Grid& g, int i, int j, int k) {
    const double c = g.raw_phi(i, j, k);
    const auto S = [&](int dx, int dy, int dz) { return g.stencil_phi(i + dx, j + dy, k + dz, c); };
    double gx = 16.0 * (S(1,0,0) - S(-1,0,0))
              + S(1,1,1) - S(-1,1,1) + S(1,-1,1) - S(-1,-1,1)
              + S(1,1,-1) - S(-1,1,-1) + S(1,-1,-1) - S(-1,-1,-1)
              + 4.0 * (S(1,1,0) - S(-1,1,0) + S(1,-1,0) - S(-1,-1,0)
              + S(1,0,1) - S(-1,0,1) + S(1,0,-1) - S(-1,0,-1));
    return gx / 72.0;
}

Vec3 isotropic_grad(const Grid& g, int i, int j, int k) {
    const double c = g.raw_phi(i, j, k);
    const auto S = [&](int dx, int dy, int dz) { return g.stencil_phi(i + dx, j + dy, k + dz, c); };
    Vec3 grad;
    grad.x = grad_component_x(g, i, j, k);
    grad.y = (16.0 * (S(0,1,0) - S(0,-1,0))
           + S(1,1,1) + S(-1,1,1) - S(1,-1,1) - S(-1,-1,1)
           + S(1,1,-1) + S(-1,1,-1) - S(1,-1,-1) - S(-1,-1,-1)
           + 4.0 * (S(1,1,0) + S(-1,1,0) - S(1,-1,0) - S(-1,-1,0)
           + S(0,1,1) - S(0,-1,1) + S(0,1,-1) - S(0,-1,-1))) / 72.0;
    grad.z = (16.0 * (S(0,0,1) - S(0,0,-1))
           + S(1,1,1) + S(-1,1,1) + S(1,-1,1) + S(-1,-1,1)
           - S(1,1,-1) - S(-1,1,-1) - S(1,-1,-1) - S(-1,-1,-1)
           + 4.0 * (S(1,0,1) + S(-1,0,1) - S(1,0,-1) - S(-1,0,-1)
           + S(0,1,1) + S(0,-1,1) - S(0,1,-1) - S(0,-1,-1))) / 72.0;
    return grad;
}

double isotropic_laplace(const Grid& g, int i, int j, int k) {
    const double c = g.raw_phi(i, j, k);
    const auto S = [&](int dx, int dy, int dz) { return g.stencil_phi(i + dx, j + dy, k + dz, c); };
    double v = 16.0 * (S(1,0,0) + S(-1,0,0) + S(0,1,0) + S(0,-1,0) + S(0,0,1) + S(0,0,-1))
             + 1.0 * (S(1,1,1) + S(-1,1,1) + S(1,-1,1) + S(-1,-1,1)
             + S(1,1,-1) + S(-1,1,-1) + S(1,-1,-1) + S(-1,-1,-1))
             + 4.0 * (S(1,1,0) + S(-1,1,0) + S(1,-1,0) + S(-1,-1,0)
             + S(1,0,1) + S(-1,0,1) + S(1,0,-1) + S(-1,0,-1)
             + S(0,1,1) + S(0,-1,1) + S(0,1,-1) + S(0,-1,-1))
             - 152.0 * S(0,0,0);
    return v / 36.0;
}

Vec3 normalize(Vec3 v) {
    const double m = std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
    if (m == 0.0) return {};
    return {v.x / m, v.y / m, v.z / m};
}

double sdf_plane_y(double y, double y0) {
    return y - y0;
}

double sdf_cylinder_z(double x, double y, double cx, double cy, double radius) {
    const double dx = x - cx;
    const double dy = y - cy;
    return std::sqrt(dx * dx + dy * dy) - radius;
}

double sdf_sphere(double x, double y, double z, double cx, double cy, double cz, double radius) {
    const double dx = x - cx;
    const double dy = y - cy;
    const double dz = z - cz;
    return std::sqrt(dx * dx + dy * dy + dz * dz) - radius;
}

Vec3 normal_cylinder_z(double x, double y, double cx, double cy) {
    return normalize({x - cx, y - cy, 0.0});
}

Vec3 normal_sphere(double x, double y, double z, double cx, double cy, double cz) {
    return normalize({x - cx, y - cy, z - cz});
}

double bounded(double v, double lo, double hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

double geometric_wall_ghost(double phi_f, double tangent_grad_mag, double h, double theta_deg,
                            double lo = 0.0, double hi = 1.0, bool* clamp_hit = nullptr) {
    const double theta = theta_deg * PI / 180.0;
    const double raw = phi_f + 2.0 * h * std::tan(0.5 * PI - theta) * tangent_grad_mag;
    const double clamped = bounded(raw, lo, hi);
    if (clamp_hit) *clamp_hit = std::fabs(raw - clamped) > 1e-14;
    return clamped;
}

double phase_tanh_profile(double x, const PhaseParams& p, int sign = -1) {
    const double mid = 0.5 * (p.phi_h + p.phi_l);
    const double amp = 0.5 * (p.phi_h - p.phi_l);
    return mid + static_cast<double>(sign) * amp * std::tanh(2.0 * x / p.int_width);
}

double phase_tanh_second_derivative(double x, const PhaseParams& p, int sign = -1) {
    const double a = 2.0 / p.int_width;
    const double t = std::tanh(a * x);
    const double sech2 = 1.0 - t * t;
    const double amp = 0.5 * (p.phi_h - p.phi_l);
    return static_cast<double>(sign) * amp * (-2.0 * a * a * sech2 * t);
}

double phase_tanh_first_derivative(double x, const PhaseParams& p, int sign = -1) {
    const double a = 2.0 / p.int_width;
    const double t = std::tanh(a * x);
    const double sech2 = 1.0 - t * t;
    const double amp = 0.5 * (p.phi_h - p.phi_l);
    return static_cast<double>(sign) * amp * a * sech2;
}

double calc_mu_tclb(double c, double lap_phi, const PhaseParams& p) {
    const double pfavg = 0.5 * (p.phi_l + p.phi_h);
    return 4.0 * (12.0 * p.sigma / p.int_width) * (c - p.phi_l) * (c - p.phi_h) * (c - pfavg)
         - (1.5 * p.sigma * p.int_width) * lap_phi;
}

double allen_cahn_tmp1(double c, const PhaseParams& p) {
    const double c0 = 0.5 * (p.phi_l + p.phi_h);
    const double range = p.phi_h - p.phi_l;
    const double normalized = range != 0.0 ? (c - c0) / range : 0.0;
    return (1.0 - 4.0 * normalized * normalized) / p.int_width;
}

double calc_f_phi(const Lattice& lat, int q, double tmp1, const Vec3& n) {
    return lat.w[q] * tmp1 * (lat.ex[q] * n.x + lat.ey[q] * n.y + lat.ez[q] * n.z);
}

Vec3 calc_fs(double mu, const Vec3& grad_phi) {
    return {mu * grad_phi.x, mu * grad_phi.y, mu * grad_phi.z};
}

struct TestStats {
    int checks = 0;
    int failures = 0;
};

void check(TestStats& stats, bool ok, const std::string& name) {
    ++stats.checks;
    if (!ok) {
        ++stats.failures;
        std::cerr << "FAIL " << name << "\n";
    } else {
        std::cout << "PASS " << name << "\n";
    }
}

bool near(double a, double b, double tol) {
    return std::fabs(a - b) <= tol;
}

double norm(Vec3 v) {
    return std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
}

struct MathValidation {
    ScalarMetrics planar_mu_discrete;
    ScalarMetrics planar_mu_exact_laplace;
    ScalarMetrics planar_laplace_error;
    ScalarMetrics planar_grad_error;
    ScalarMetrics planar_surface_force;
    double bulk_mu_liquid = 0.0;
    double bulk_mu_gas = 0.0;
    double bulk_grad_norm = 0.0;
    double allen_cahn_sum_error = 0.0;
    double allen_cahn_first_moment_error = 0.0;
    double allen_cahn_bulk_tmp1_liquid = 0.0;
    double allen_cahn_bulk_tmp1_gas = 0.0;
    double allen_cahn_interface_tmp1 = 0.0;
};

MathValidation run_phasefield_math_validation(const Lattice& lat) {
    MathValidation mv;
    const PhaseParams p;

    Grid bulk(7, 7, 7);
    for (double& v : bulk.phi) v = p.phi_l;
    const Vec3 grad_l = isotropic_grad(bulk, 3, 3, 3);
    const double lap_l = isotropic_laplace(bulk, 3, 3, 3);
    mv.bulk_mu_gas = calc_mu_tclb(p.phi_l, lap_l, p);
    for (double& v : bulk.phi) v = p.phi_h;
    const Vec3 grad_h = isotropic_grad(bulk, 3, 3, 3);
    const double lap_h = isotropic_laplace(bulk, 3, 3, 3);
    mv.bulk_mu_liquid = calc_mu_tclb(p.phi_h, lap_h, p);
    mv.bulk_grad_norm = std::max(norm(grad_l), norm(grad_h));

    const int nx = 129;
    const int ny = 5;
    const int nz = 5;
    Grid planar(nx, ny, nz);
    const double x0 = 0.5 * static_cast<double>(nx - 1);
    for (int k = 0; k < planar.nz; ++k) {
        for (int j = 0; j < planar.ny; ++j) {
            for (int i = 0; i < planar.nx; ++i) {
                const double x = static_cast<double>(i) - x0;
                planar.phi[planar.id(i, j, k)] = phase_tanh_profile(x, p, -1);
            }
        }
    }
    for (int i = 8; i < planar.nx - 8; ++i) {
        const double x = static_cast<double>(i) - x0;
        const double c = planar.raw_phi(i, 2, 2);
        const double lap_d = isotropic_laplace(planar, i, 2, 2);
        const double lap_e = phase_tanh_second_derivative(x, p, -1);
        const Vec3 grad_d = isotropic_grad(planar, i, 2, 2);
        const double grad_e = phase_tanh_first_derivative(x, p, -1);
        const double mu_d = calc_mu_tclb(c, lap_d, p);
        const double mu_e = calc_mu_tclb(c, lap_e, p);
        const Vec3 fs = calc_fs(mu_d, grad_d);
        mv.planar_mu_discrete.add(mu_d);
        mv.planar_mu_exact_laplace.add(mu_e);
        mv.planar_laplace_error.add(lap_d - lap_e);
        mv.planar_grad_error.add(grad_d.x - grad_e);
        mv.planar_surface_force.add(norm(fs));
    }

    const Vec3 n = normalize({1.0, 2.0, -0.5});
    const double tmp1 = allen_cahn_tmp1(0.5 * (p.phi_l + p.phi_h), p);
    double source_sum = 0.0;
    Vec3 first_moment;
    for (int q = 0; q < Q; ++q) {
        const double f = calc_f_phi(lat, q, tmp1, n);
        source_sum += f;
        first_moment.x += lat.ex[q] * f;
        first_moment.y += lat.ey[q] * f;
        first_moment.z += lat.ez[q] * f;
    }
    const Vec3 expected = {tmp1 * n.x / 3.0, tmp1 * n.y / 3.0, tmp1 * n.z / 3.0};
    mv.allen_cahn_sum_error = std::fabs(source_sum);
    mv.allen_cahn_first_moment_error = norm({first_moment.x - expected.x,
                                             first_moment.y - expected.y,
                                             first_moment.z - expected.z});
    mv.allen_cahn_bulk_tmp1_gas = allen_cahn_tmp1(p.phi_l, p);
    mv.allen_cahn_bulk_tmp1_liquid = allen_cahn_tmp1(p.phi_h, p);
    mv.allen_cahn_interface_tmp1 = tmp1;
    return mv;
}

void write_math_validation_csv(const std::string& path, const MathValidation& mv) {
    std::ofstream csv(path);
    csv << std::setprecision(17);
    csv << "metric,value\n";
    csv << "planar_mu_discrete_max_abs," << mv.planar_mu_discrete.max_abs << "\n";
    csv << "planar_mu_discrete_mean_abs," << mv.planar_mu_discrete.mean_abs() << "\n";
    csv << "planar_mu_discrete_rms," << mv.planar_mu_discrete.rms() << "\n";
    csv << "planar_mu_exact_laplace_max_abs," << mv.planar_mu_exact_laplace.max_abs << "\n";
    csv << "planar_mu_exact_laplace_rms," << mv.planar_mu_exact_laplace.rms() << "\n";
    csv << "planar_laplace_error_max_abs," << mv.planar_laplace_error.max_abs << "\n";
    csv << "planar_laplace_error_rms," << mv.planar_laplace_error.rms() << "\n";
    csv << "planar_grad_error_max_abs," << mv.planar_grad_error.max_abs << "\n";
    csv << "planar_grad_error_rms," << mv.planar_grad_error.rms() << "\n";
    csv << "planar_surface_force_max_abs," << mv.planar_surface_force.max_abs << "\n";
    csv << "planar_surface_force_rms," << mv.planar_surface_force.rms() << "\n";
    csv << "bulk_mu_gas," << mv.bulk_mu_gas << "\n";
    csv << "bulk_mu_liquid," << mv.bulk_mu_liquid << "\n";
    csv << "bulk_grad_norm," << mv.bulk_grad_norm << "\n";
    csv << "allen_cahn_sum_error," << mv.allen_cahn_sum_error << "\n";
    csv << "allen_cahn_first_moment_error," << mv.allen_cahn_first_moment_error << "\n";
    csv << "allen_cahn_bulk_tmp1_gas," << mv.allen_cahn_bulk_tmp1_gas << "\n";
    csv << "allen_cahn_bulk_tmp1_liquid," << mv.allen_cahn_bulk_tmp1_liquid << "\n";
    csv << "allen_cahn_interface_tmp1," << mv.allen_cahn_interface_tmp1 << "\n";
}

void write_vtk_demo(const std::string& path) {
    const int nx = 32;
    const int ny = 32;
    const int nz = 16;
    Grid g(nx, ny, nz);
    const double cx = 16.0;
    const double cy = 16.0;
    const double cz = 8.0;
    const double r = 8.0;
    for (int k = 0; k < nz; ++k) {
        for (int j = 0; j < ny; ++j) {
            for (int i = 0; i < nx; ++i) {
                const double sd = sdf_sphere(i + 0.5, j + 0.5, k + 0.5, cx, cy, cz, r);
                const std::size_t p = g.id(i, j, k);
                g.phi[p] = 0.5 * (1.0 - std::tanh(2.0 * sd / 4.0));
                g.solid[p] = (j == 0) ? 1 : 0;
                if (g.solid[p]) g.wall_ghost[p] = 0.5;
            }
        }
    }
    std::ofstream out(path);
    out << "# vtk DataFile Version 3.0\nphasefield_reference_demo\nASCII\nDATASET STRUCTURED_POINTS\n";
    out << "DIMENSIONS " << nx << " " << ny << " " << nz << "\n";
    out << "ORIGIN 0 0 0\nSPACING 1 1 1\nPOINT_DATA " << (nx * ny * nz) << "\n";
    out << "SCALARS phi double 1\nLOOKUP_TABLE default\n";
    for (double v : g.phi) out << v << "\n";
    out << "SCALARS solid int 1\nLOOKUP_TABLE default\n";
    for (int v : g.solid) out << v << "\n";
}

int run_self_test() {
    TestStats stats;
    const Lattice lat = make_d3q27_tclb_order();
    double wsum = 0.0;
    for (double w : lat.w) wsum += w;
    check(stats, near(wsum, 1.0, 1e-15), "D3Q27 weights sum to one");
    for (int i = 0; i < Q; ++i) {
        check(stats, lat.opp[i] >= 0, "opposite link exists q=" + std::to_string(i));
        if (lat.opp[i] >= 0) {
            const int j = lat.opp[i];
            check(stats, lat.opp[j] == i, "opposite involution q=" + std::to_string(i));
            check(stats, lat.ex[i] + lat.ex[j] == 0 && lat.ey[i] + lat.ey[j] == 0 && lat.ez[i] + lat.ez[j] == 0,
                  "opposite velocity q=" + std::to_string(i));
        }
    }

    Grid g(12, 12, 12);
    for (int k = 0; k < g.nz; ++k) {
        for (int j = 0; j < g.ny; ++j) {
            for (int i = 0; i < g.nx; ++i) {
                const double x = static_cast<double>(i);
                const double y = static_cast<double>(j);
                const double z = static_cast<double>(k);
                g.phi[g.id(i, j, k)] = 1.2 * x + 2.3 * y - 0.7 * z + 0.4;
            }
        }
    }
    Vec3 grad = isotropic_grad(g, 6, 6, 6);
    check(stats, near(grad.x, 1.2, 1e-12), "isotropic grad linear x");
    check(stats, near(grad.y, 2.3, 1e-12), "isotropic grad linear y");
    check(stats, near(grad.z, -0.7, 1e-12), "isotropic grad linear z");

    for (int k = 0; k < g.nz; ++k) {
        for (int j = 0; j < g.ny; ++j) {
            for (int i = 0; i < g.nx; ++i) {
                const double x = static_cast<double>(i);
                const double y = static_cast<double>(j);
                const double z = static_cast<double>(k);
                g.phi[g.id(i, j, k)] = x * x + y * y + z * z;
            }
        }
    }
    check(stats, near(isotropic_laplace(g, 6, 6, 6), 6.0, 1e-12), "isotropic laplace quadratic");

    check(stats, near(sdf_plane_y(4.0, 1.5), 2.5, 1e-15), "plane SDF sign");
    check(stats, near(sdf_cylinder_z(5.0, 0.0, 0.0, 0.0, 3.0), 2.0, 1e-15), "cylinder SDF");
    Vec3 nc = normal_cylinder_z(5.0, 0.0, 0.0, 0.0);
    check(stats, near(nc.x, 1.0, 1e-15) && near(nc.y, 0.0, 1e-15), "cylinder normal");
    check(stats, near(sdf_sphere(0.0, 0.0, 5.0, 0.0, 0.0, 0.0, 3.0), 2.0, 1e-15), "sphere SDF");
    Vec3 ns = normal_sphere(0.0, 0.0, 5.0, 0.0, 0.0, 0.0);
    check(stats, near(ns.z, 1.0, 1e-15), "sphere normal");

    bool clamp_hit = true;
    const double ghost90 = geometric_wall_ghost(0.35, 0.2, 0.5, 90.0, 0.0, 1.0, &clamp_hit);
    check(stats, near(ghost90, 0.35, 1e-14) && !clamp_hit, "theta90 ghost leaves phi unchanged");
    const double ghost30 = geometric_wall_ghost(0.35, 0.2, 0.5, 30.0, 0.0, 1.0, &clamp_hit);
    check(stats, ghost30 > 0.35, "acute wall ghost biases liquid side");
    const double ghost150 = geometric_wall_ghost(0.35, 0.2, 0.5, 150.0, 0.0, 1.0, &clamp_hit);
    check(stats, ghost150 < 0.35, "obtuse wall ghost biases gas side");

    Grid sg(5, 5, 5);
    for (double& v : sg.phi) v = 1.0;
    const std::size_t sid = sg.id(2, 1, 2);
    sg.solid[sid] = 1;
    sg.phi[sid] = -999.0;
    sg.wall_ghost[sid] = 1.0;
    const double lap = isotropic_laplace(sg, 2, 2, 2);
    check(stats, std::isfinite(lap) && std::fabs(lap) < 1e-12, "solid sentinel blocked by passive ghost in stencil");
    check(stats, sg.phi[sid] == -999.0, "passive ghost does not overwrite solid phi");

    const MathValidation mv = run_phasefield_math_validation(lat);
    write_math_validation_csv("math_validation_diagnostics.csv", mv);
    check(stats, std::fabs(mv.bulk_mu_gas) < 1e-14, "phase-field bulk gas mu is zero");
    check(stats, std::fabs(mv.bulk_mu_liquid) < 1e-14, "phase-field bulk liquid mu is zero");
    check(stats, mv.bulk_grad_norm < 1e-14, "phase-field bulk gradient is zero");
    check(stats, mv.planar_mu_exact_laplace.max_abs < 1e-14, "continuous tanh profile closes TCLB mu formula");
    check(stats, mv.planar_laplace_error.max_abs < 1.0e-2, "discrete Laplace resolves tanh interface");
    check(stats, mv.planar_mu_discrete.max_abs < 6.0e-2, "discrete tanh mu residual stays bounded");
    check(stats, mv.planar_surface_force.max_abs < 2.0e-2, "discrete tanh surface force residual stays bounded");
    check(stats, mv.allen_cahn_sum_error < 1e-16, "Allen-Cahn source zeroth moment is zero");
    check(stats, mv.allen_cahn_first_moment_error < 1e-16, "Allen-Cahn source first moment matches D3Q27 tensor");
    check(stats, std::fabs(mv.allen_cahn_bulk_tmp1_gas) < 1e-16, "Allen-Cahn source vanishes in gas bulk");
    check(stats, std::fabs(mv.allen_cahn_bulk_tmp1_liquid) < 1e-16, "Allen-Cahn source vanishes in liquid bulk");
    check(stats, near(mv.allen_cahn_interface_tmp1, 0.25, 1e-16), "Allen-Cahn source peaks at interface");

    std::ofstream csv("selftest_diagnostics.csv");
    csv << "checks,failures,weight_sum,laplace_sentinel_test,planar_mu_discrete_max_abs,planar_surface_force_max_abs,allen_cahn_first_moment_error\n";
    csv << stats.checks << "," << stats.failures << "," << std::setprecision(17) << wsum << "," << lap << ","
        << mv.planar_mu_discrete.max_abs << "," << mv.planar_surface_force.max_abs << ","
        << mv.allen_cahn_first_moment_error << "\n";
    write_vtk_demo("selftest_fields.vtk");

    std::cout << "checks=" << stats.checks << " failures=" << stats.failures << "\n";
    return stats.failures == 0 ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
    bool self_test = false;
    std::string vtk_path;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--self-test") {
            self_test = true;
        } else if (arg == "--write-vtk" && i + 1 < argc) {
            vtk_path = argv[++i];
        } else if (arg == "--help") {
            std::cout << "Usage: phasefield_reference [--self-test] [--write-vtk path]\n";
            return 0;
        } else {
            std::cerr << "unknown argument: " << arg << "\n";
            return 2;
        }
    }
    if (!vtk_path.empty()) {
        write_vtk_demo(vtk_path);
    }
    if (self_test || vtk_path.empty()) {
        return run_self_test();
    }
    return 0;
}
