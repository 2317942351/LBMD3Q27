#include <array>
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

    std::ofstream csv("selftest_diagnostics.csv");
    csv << "checks,failures,weight_sum,laplace_sentinel_test\n";
    csv << stats.checks << "," << stats.failures << "," << std::setprecision(17) << wsum << "," << lap << "\n";
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
