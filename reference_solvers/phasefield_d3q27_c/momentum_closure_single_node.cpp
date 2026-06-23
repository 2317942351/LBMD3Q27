#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>

namespace {

struct Vec3 {
  double x = 0.0;
  double y = 0.0;
  double z = 0.0;
};

double parse_arg(int argc, char** argv, const std::string& name, double fallback) {
  const std::string prefix = "--" + name + "=";
  for (int i = 1; i < argc; ++i) {
    const std::string arg(argv[i]);
    if (arg.rfind(prefix, 0) == 0) {
      return std::strtod(arg.substr(prefix.size()).c_str(), nullptr);
    }
  }
  return fallback;
}

Vec3 vec_arg(int argc, char** argv, const std::string& prefix, Vec3 fallback) {
  fallback.x = parse_arg(argc, argv, prefix + "x", fallback.x);
  fallback.y = parse_arg(argc, argv, prefix + "y", fallback.y);
  fallback.z = parse_arg(argc, argv, prefix + "z", fallback.z);
  return fallback;
}

Vec3 add(Vec3 a, Vec3 b) {
  return {a.x + b.x, a.y + b.y, a.z + b.z};
}

Vec3 scale(Vec3 a, double s) {
  return {a.x * s, a.y * s, a.z * s};
}

void print_vec(const std::string& name, Vec3 v) {
  std::cout << name << "_x=" << v.x << "\n";
  std::cout << name << "_y=" << v.y << "\n";
  std::cout << name << "_z=" << v.z << "\n";
}

}  // namespace

int main(int argc, char** argv) {
  Vec3 m0 = vec_arg(argc, argv, "m0", {0.0, 0.0, 0.0});
  Vec3 force = vec_arg(argc, argv, "f", {0.0, 0.0, 0.0});
  const double rho = parse_arg(argc, argv, "rho", 1.0);
  const double scale_injection = parse_arg(argc, argv, "injection-scale", 1.0);
  const double inv_rho = (rho != 0.0) ? 1.0 / rho : 0.0;

  const Vec3 force_over_rho = scale(force, inv_rho);
  const Vec3 u_half = add(m0, scale(force_over_rho, 0.5));
  const Vec3 expected_delta = scale(force_over_rho, scale_injection);
  const Vec3 expected_after = add(m0, expected_delta);

  std::cout << std::setprecision(17);
  std::cout << "scope=single_node_momentum_algebra_only\n";
  std::cout << "rho=" << rho << "\n";
  std::cout << "injection_scale=" << scale_injection << "\n";
  print_vec("m0", m0);
  print_vec("force", force);
  print_vec("force_over_rho", force_over_rho);
  print_vec("u_half", u_half);
  print_vec("expected_momentum_delta", expected_delta);
  print_vec("expected_momentum_after", expected_after);
  return 0;
}
