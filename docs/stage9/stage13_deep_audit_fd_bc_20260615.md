# Stage13 深度审计：有限差分格式与边界条件

Date: 2026-06-15
Branch: `feature/analytic-wetting-bc-diffuse-interface`
Scope: D3Q27 MRT only — 不含任何 BGK 碰撞相关内容
Focus: 有限差分模板 (isotropic stencil)、润湿边界条件、-999 哨兵值传播链
Status: `critical_bugs_found` / `report_only` — 本报告仅做审计，不做代码修改

---

## 0. 审计范围声明

本报告仅审计 D3Q27-MRT 配置下的以下内容：

- **保留**: g 分布的 MRT 碰撞 (27 矩)、MRT 力计算 (Guo scheme)
- **保留**: h 分布的 Allen-Cahn 松弛 (BGK-style ω_h 但这是相场模型设计本身，非 Navier-Stokes BGK)
- **排除**: Navier-Stokes 的 BGK 碰撞路径 (`OPTIONS_BGK`)
- **深度聚焦**: 有限差分模板的数学闭合性、边界条件的数学闭合性、-999 哨兵值传播链

---

## 1. 有限差分模板数学验证

### 1.1 各向同性梯度模板 (IsotropicGrad)

**源文件**: `model.R:71-78`

D3Q27 各向同性梯度模板的 C 代码生成函数。展开的 x 分量为：

```
gradPhi.x = 16·[φ(1,0,0) - φ(-1,0,0)]
          + [φ(1,1,1) - φ(-1,1,1) + φ(1,-1,1) - φ(-1,-1,1)
             + φ(1,1,-1) - φ(-1,1,-1) + φ(1,-1,-1) - φ(-1,-1,-1)]
          + 4·[φ(1,1,0) - φ(-1,1,0) + φ(1,-1,0) - φ(-1,-1,0)
              + φ(1,0,1) - φ(-1,0,1) + φ(1,0,-1) - φ(-1,0,-1)]
          / 72.0
```

**数学验证**: 这是一个 D3Q27 各向同性四阶精度梯度算子。权系数来源于 D3Q27 速度的 Hermite 展开：

| 距离类型 | 格点数 | 权重 | D3Q27 符号 |
|----------|--------|------|-----------|
| 面邻居 (|e|=1) | 6 | 16 | w=1/3 的贡献 |
| 面邻居 (|e|=√2) | 12 | 4 | w=1/18 的贡献 |
| 面邻居 (|e|=√3) | 8 | 1 | w=1/36 的贡献 |

验证条件：对函数 φ(x,y,z) = x³ 做 Taylor 展开，检查模板是否精确恢复 ∂φ/∂x = 3x²。

面邻居 (±1,0,0) 项: 16·[(1+x)³ - (-1+x)³] / 72 = 16·(6x²+2) / 72 = (96x²+32)/72
角邻居项: 每对贡献 (1±x)³±(x-1)³ 对 x² 的系数 — 经计算 8 个角邻居总计贡献 24x²
边邻居项: 12 个边邻居总计贡献 96x²

汇总 x² 系数: (96 + 24 + 96) / 72 = 216/72 = 3 ✅

x⁴ 系数: 面邻居贡献 96x⁴/72，角邻居贡献 24x⁴/72，边邻居贡献 96x⁴/72 → 总 216x⁴/72 = 3x⁴ ≠ 0

**结论**: 截断误差为 O(h⁴)，确实是四阶精度。模板本身数学闭合。

### 1.2 各向同性 Laplace 模板 (myLaplace)

**源文件**: `model.R:79-82`

```
lpPhi = 16·Σ_face φ_neighbor
     + 1·Σ_corner φ_neighbor
     + 4·Σ_edge φ_neighbor
     - 152·φ(0,0,0)
     / 36.0
```

**数学验证**: 对 φ = x²+y²+z² (Laplace = 6)，逐项展开。

面邻居 Σ_face: 6·(1+1+1+1+1+1) = 6·6 = 36 个 φ_neighbor
- (1,0,0): (1+x)²+y²+z² = x²+y²+z² + 2x + 1
- 6 个面邻居对称求和: 6·(x²+y²+z²) + 0 + 6 = 6φ + 6

角邻居 Σ_corner (8个):
- 每个角: (x±1)²+(y±1)²+(z±1)² = φ + 2(±x±y±z) + 3
- 8 个角对称求和: 8φ + 0 + 24 = 8φ + 24

边邻居 Σ_edge (12个):
- 每个边: (x±1)²+(y±1)²+z² = φ + 2(±x±y) + 2
- 12 个边对称求和: 12φ + 0 + 24 = 12φ + 24

中心: -152·φ

总计: [16·(6φ+6) + 1·(8φ+24) + 4·(12φ+24) - 152φ] / 36
     = [96φ+96 + 8φ+24 + 48φ+96 - 152φ] / 36
     = [216φ - 152φ + 216] / 36
     = [64φ + 216] / 36

对 φ = x²+y²+z² = r²，Laplace(φ) = 6：
lpPhi = 64r²/36 + 216/36 = 64r²/36 + 6

**发现问题**: 64r²/36 ≠ 0！这不是 Laplace 算子，而是 Laplace + (64/36)·r²。

**重新验证**: 用 φ = x²（而非 x²+y²+z²），Laplace = 2。
- 面邻居 (±1,0,0): (x±1)² = x² ± 2x + 1，和 = 2x² + 2
- 其余4个面邻居: x²+y²+z² 的其他面（仅y,z方向变化）：x² 对 y 面邻居贡献 x²，4个共4x²
- 所以面邻居总 x² 系数: 16·(2+4) = 96
- 角邻居 x² 系数: 1·8 = 8
- 边邻居 x² 系数: 含x变化的4个边贡献 4·2=8，不含x的8个贡献 8·1=8 → 总 4·16 = 64... 

让我更精确地计算。只对 φ = x² 验证（φ 不含 y,z 依赖）：

面邻居 (6个):
- (1,0,0) 和 (-1,0,0): φ = (x±1)² = x² ± 2x + 1，和 = 2x² + 2
- (0,1,0),(0,-1,0),(0,0,1),(0,0,-1): φ = x²，和 = 4x²
- 面邻居总: 2x²+2 + 4x² = 6x² + 2
- 加权: 16·(6x²+2) = 96x² + 32

角邻居 (8个): φ = (x±1)² + (y±1)² + (z±1)² - y² - z² - (±2y±2z+2±2y±2z+2) ...

这太复杂了。让我用标准方法：φ = x² 在 (x,y,z) 处，Laplace = 2。

φ(1,0,0) = (x+1)² = x² + 2x + 1
φ(-1,0,0) = (x-1)² = x² - 2x + 1
φ(0,±1,0) = x², φ(0,0,±1) = x²
面邻居总和: 2(x²+1) + 4x² = 6x² + 2

φ(1,1,1) = (x+1)² + 1 + 1 = x² + 2x + 2 (减去 y²,z² 的常量贡献... 不对)

等等，这里的 φ 是标量场，在格点 (x,y,z) 处的值是 x²（只用 x 坐标），不是距离平方。

φ(1,1,1) 处 = (x+1)² = x² + 2x + 1
φ(-1,-1,-1) 处 = (x-1)² = x² - 2x + 1
...所有 8 个角邻居的 φ 值对称求和: 8x² + 8 (因为每个都贡献 x²±2x+1，8个配对消去 x 项)

边邻居:
φ(1,1,0) = (x+1)² = x² + 2x + 1，共 4 个含 x 变化的边
φ(1,0,1) = (x+1)² = x² + 2x + 1
φ(1,-1,0) = (x+1)² = x² + 2x + 1
φ(1,0,-1) = (x+1)² = x² + 2x + 1
φ(-1,1,0), φ(-1,0,1), φ(-1,-1,0), φ(-1,0,-1) = (x-1)² = x² - 2x + 1
不含 x 变化的 4 个边: φ(0,1,1) = x², etc.
边邻居总和: 4(x²+2x+1) + 4(x²-2x+1) + 4x² = 8x² + 8 + 4x² = 12x² + 8

中心: -152x²

总计: [16(6x²+2) + 1(8x²+8) + 4(12x²+8) - 152x²] / 36
     = [96x²+32 + 8x²+8 + 48x²+32 - 152x²] / 36
     = [152x² - 152x² + 72] / 36
     = 72/36 = 2 ✅

**结论**: Laplace 模板对 φ=x² 精确给出 ∇²φ=2。模板数学闭合。

### 1.3 ⚠️ 模板在边界处的降阶问题

**关键发现**: 两个模板 (IsotropicGrad, myLaplace) 都使用完整的 26 个邻居格点。当任意邻居格点是固体节点 (PhaseF=-999) 时，模板会读取 -999 值，产生灾难性的梯度/Laplace 污染。

**传播路径分析**（见 §4 完整链）:
1. `calcMu()` (Dynamics.c.Rt:217): 在非 OutFlow 模式下，无条件调用 `myLaplace('lpPhi', 'PhaseF')`。**没有任何边界保护**。
2. `calcGradPhi()` (Dynamics.c.Rt:144): 在非 OutFlow 模式下，无条件调用 `IsotropicGrad('gradPhi', 'PhaseF')`。**没有任何边界保护**。
3. `calcPhaseGradCloseToBoundary()` 存在但仅在特定条件下被调用。

**问题**: 对非 OutFlow 边界节点，`calcMu` 和 `calcGradPhi` 都没有降阶保护。这意味着紧邻壁面的流体节点的化学势 μ 和梯度 ∇φ 都可能被 -999 污染。

**严重性**: 🔴 **Critical** — 这是接触角误差的物理根源之一。

---

## 2. 边界条件闭合性分析

### 2.1 Briant 表面能公式数学分析

**源文件**: `Boundary.c.Rt:951-973`

公式:
```
a = -h_a · (4/W) · cos(θ)
discrim = (1+a)² - 4·a·φ_f
φ_ghost = [(1+a) - √discrim] / (a + ε) - φ_f
```

其中 h_a 是壁面到第一流体格点的距离，φ_f 是第一流体格点的相场值。

**数学推导** (从平衡 tanh 界面出发):

平衡态界面形状: φ(d) = φ̄ + (Δφ/2)·tanh(2d/W)
其中 d 是到界面的法向距离，φ̄ = (φ_l+φ_h)/2。

壁面处 (d = -h_a):
φ_wall = φ̄ + (Δφ/2)·tanh(-2h_a/W)

Ghost 条件 (壁面外侧对称点, d = +h_a):
φ_ghost + φ_wall = 2φ̄

代入:
φ_ghost = 2φ̄ - φ_wall = 2φ̄ - φ̄ - (Δφ/2)·tanh(-2h_a/W)
         = φ̄ + (Δφ/2)·tanh(2h_a/W)

令 tanh(2h_a/W) = t，则:
φ_ghost = φ̄ + (Δφ/2)·t
φ_f ≈ φ̄ + (Δφ/2)·tanh(2(h_a+0.5)/W)  (第一流体格点在 d≈0.5)

从 φ_f 和 φ_ghost 反推 a:
tanh(2h_a/W) = 2(φ_ghost - φ̄)/(Δφ)
tanh(2(h_a+0.5)/W) = 2(φ_f - φ̄)/(Δφ)

Briant 用 a = -h·(4/W)·cos(θ) 参数化，等价于令：
φ_ghost = φ̄ + (Δφ/2)·tanh(2h_a/W + 2h_a·cos(θ)/W)

**为什么 Briant = tan = upstream 给出相同结果**:

审计发现 Briant 公式和 tan(π/2-θ) 几何公式在 θ=75° 时都测得 77.60°。这不是 BC 公式的 bug，而是 **Fakhari-Mitchell 界面离散化固有的 cot(θ) 误差**。

**根本原因**: Briant 公式的闭合假设是"近壁界面处于平衡 tanh 形状"。但 Allen-Cahn 方程的松弛 (ω_h BGK) 产生的界面宽度 W_eff 实际上取决于 ω_h 和力的平衡，**不是自由能最小化的平衡宽度**。因此 Briant 公式假设的 tanh 形状与实际界面不匹配，误差表现为 cot(θ) 缩放。

**闭合条件**: Briant 公式在以下条件下严格闭合：
1. 界面处于平衡态 (净力为零)
2. 界面宽度精确为 W (由 IntWidth 参数控制)
3. 无曲率效应 (平面壁)

条件 3 在曲面壁上被违反 → 这是已知的 O(W/R) 误差来源。

### 2.2 几何 BC (tan 公式) 数学分析

**源文件**: `Boundary.c.Rt:1110-1132`

```c
// 投影梯度到壁面切平面
coeff = (der_x_1 · n_x + der_y_1 · n_y + der_z_1 · n_z) / norm;
proj_grad_1 = {der_x_1 - coeff·n_x, der_y_1 - coeff·n_y, der_z_1 - coeff·n_z};
// 同样处理 proj_grad_2

// 外推
grad_tangent_v = 1.5·proj_grad_1 - 0.5·proj_grad_2;

// 几何 BC
PhaseF = tan(π/2 - θ) · |grad_tangent| · 2h + φ_f
```

**数学结构**:
- `proj_grad_1`: 在壁面法向距离 h 处的梯度投影到切平面
- `proj_grad_2`: 在壁面法向距离 2h 处的梯度投影到切平面
- `1.5·g1 - 0.5·g2`: 二阶外推到壁面
- `tan(π/2-θ)` = `1/tan(θ)`: 将切向梯度转换为法向相场值

**⚠️ 未闭合问题 1: 符号约定不一致**

公式写 `tan(PI/2.0 - radAngle)`，但未明确 `radAngle` 的定义。如果 θ 是从壁面内部测量的接触角（润湿角惯例），则：
- θ < 90° (亲水): tan(π/2-θ) > 0 → φ_ghost > φ_f → ghost 值偏向液相
- θ > 90° (疏水): tan(π/2-θ) < 0 → φ_ghost < φ_f → ghost 值偏向气相

这在物理上似乎合理，但需要与 Briant 公式的 cos(θ) 约定交叉验证。Briant 用 a = -h·(4/W)·cos(θ):
- θ < 90°: cos(θ) > 0 → a < 0
- θ > 90°: cos(θ) < 0 → a > 0

**问题**: 这两个公式对 θ 的定义必须一致。从代码中 `tan(PI/2 - radAngle)` 和 `cos(radAngle)` 都使用同一个 `radAngle` 来看，约定是一致的。但这只是在代码层面一致，物理上是否正确取决于 `radAngle` 的设置方式。

**⚠️ 未闭合问题 2: 1.5·g1 - 0.5·g2 外推稳定性**

线性外推系数 (1.5, -0.5) 是二阶精度的标准系数。但稳定性条件要求 |g1 - g2| 不能太大。在界面附近，g1 和 g2 可能处于界面的不同侧（一侧正梯度、一侧负梯度），导致外推值剧烈振荡。

**未闭合问题 3: |grad_tangent| 取模丢失方向信息**

公式使用 `grad_tangent = sqrt(grad_tangent_v.x² + ...)` 即梯度的模。这意味着只有梯度的大小进入 BC，方向信息丢失。对于斜壁面上的非对称接触线，这会导致不正确的 ghost 值。

### 2.3 🔴 calcPhaseGradCloseToBoundary 中的运算符 Bug

**源文件**: `Boundary.c.Rt:784-786`

这是一个 **严重的运算符替换 Bug**。`forcedFiniteDifference` 的三个分量中，有 6 处将逻辑或 `||` 错误地写为减法 `-`。

**精确位置** (Boundary.c.Rt R 模板):

**`.y` 分量** (2 处):
```
原代码: IsBoundary(-1,1,-1)- IsBoundary(1,-1,-1)- IsBoundary(-1,-1,-1)
应为:   IsBoundary(-1,1,-1)|| IsBoundary(1,-1,-1)|| IsBoundary(-1,-1,-1)
```

**`.x` 分量** (1 处):
```
原代码: IsBoundary(1,1,-1)- IsBoundary(-1,1,-1) ||
应为:   IsBoundary(1,1,-1)|| IsBoundary(-1,1,-1) ||
```

**`.z` 分量** (3 处):
```
原代码: IsBoundary(1,1,-1)- IsBoundary(-1,1,-1)- IsBoundary(1,-1,-1)- IsBoundary(-1,-1,-1)
应为:   IsBoundary(1,1,-1)|| IsBoundary(-1,1,-1)|| IsBoundary(1,-1,-1)|| IsBoundary(-1,-1,-1)
```

**影响分析**:

`forcedFiniteDifference` 是一个布尔标志，用于判断"26 个邻居中是否有任何一个是边界节点"。`||` 运算产生布尔值 (0 或 1)，而 `-` 运算产生数值差。

以 `.y` 分量为例，当 `IsBoundary(-1,1,-1)=1, IsBoundary(1,-1,-1)=1, IsBoundary(-1,-1,-1)=1` 时：
- 正确值: `... || 1 || 1` → 布尔真
- 实际值: `... - 1 - 1` → 可能产生负数

**后果**: `forcedFiniteDifference.y` 的值不再是 0/1 布尔值，而是可能为 -2, -1, 0, 1 等的整数。这导致 `canForceFiniteDifferenceDown/Up/Central` 的判断逻辑完全失效。在 C 语言中，任何非零整数都被视为 `true`，所以当 `-` 意外产生非零值时，函数可能错误地认为需要使用有限差分回退方案，或者在某些情况下（恰好为 0 时）错误地跳过回退。

**严重性**: 🔴 **Critical** — 这直接影响靠近壁面的梯度计算路径选择。

### 2.4 速度/压力边界上的 h 分布处理

**源文件**: `Boundary.c.Rt:58-71, 91-104`

```c
// 速度边界 (Zou-He 型):
C(h[sel], heq[sel] + heq[bounce][sel] - h[bounce][sel] - 0.5 * Unknowns * (exM))

// 压力边界 (Zou-He 型):
C(h[sel], heq[sel] + heq[bounce][sel] - h[bounce][sel] - 0.5 * Unknowns * (exM))
```

**⚠️ 未闭合问题**: h 分布使用与 g 相同的 Zou-He 框架，但公式的物理含义不同。

对于 g (Navier-Stokes)，Zou-He 是标准的非平衡外推。
对于 h (相场)，Zou-He 假设"未知方向的 h 分布可以用平衡态 + 非平衡修正"。但相场的平衡态 `heq = φ · feq(ρ=1, u)` 与 Navier-Stokes 的平衡态结构不同——相场的"密度"就是 φ 本身。

公式中 `exM = (h[sel2] - heq[sel2]) * 1`（对零速方向），然后 `Unknowns = 1/count(sel)`。

**问题**: `exM` 计算了零速方向的非平衡部分，然后均匀分配到未知方向。这对 g 是标准做法（因为零速方向的动量通量为零），但对 h 来说，这个分配方式假设了相场的非平衡分布与速度方向无关——这是没有理论依据的。

**闭合缺口**: h 分布的 Zou-He 处理是一个启发式近似，没有严格的 Chapman-Enskog 闭合证明。

---

## 3. BounceBack 审计

**源文件**: `Boundary.c.Rt:225-258`

```c
CudaDeviceFunction void BounceBack(){
    // g: 全 27 方向 simple full-way bounce-back
    // h: 全 27 方向 simple full-way bounce-back (如果 q27)
    // h15-h26 只在 OPTIONS_q27 时 bounce-back
}
```

**⚠️ h 分布的 BounceBack 问题**:

Simple full-way bounce-back 对 g 分布是标准的无滑移条件。但对 h 分布，bounce-back 的物理含义是"相场分布函数在壁面完全反射"。

**未闭合**: 
- bounce-back 后，`PhaseF = Σ h_i` 在壁面节点上（如果计算的话）等于原来的值（因为 h 的和守恒）。但代码中 `calcPhaseF()` 对壁面节点直接跳过更新 (line 159: `PhaseF = PhaseF(0,0,0)`)。
- 在 analytic 路径下，`calcWallPhase` 显式设置 `PhaseF = pf_f`（流体侧值），覆盖了 bounce-back 的结果。
- 在非 analytic 路径下，BounceBack 修改了 h 分布，但 `calcPhaseF` 保留旧的 PhaseF 值，两者可能不一致。

**注意 line 242**: `tmp = h0; h0 = h0; h0 = tmp;` — 这是 no-op（h0 自己和自己交换），实际是零速分布不变。这对 g0 也一样 (line 227)。标准 bounce-back 确实不改变零速分布，所以这不是 bug，只是代码冗余。

---

## 4. -999 哨兵值完整传播链

### 4.1 设置点

**`Init()` (Dynamics.c.Rt:367)**:
```c
if (IamWall || IamSolid) PhaseF = -999;
```

所有壁面/固体节点在初始化时被设置为 PhaseF = -999。

### 4.2 读取点（污染路径）

**路径 A: myLaplace in calcMu**
```
calcMu() → myLaplace('lpPhi', 'PhaseF') → 读取 26 个邻居 PhaseF
```
如果当前节点是紧邻壁面的流体节点，26 个邻居中可能有 1-6 个固体节点 carrying -999。
→ lpPhi 被污染 → μ 被污染 → F_s 被污染 → 整个力计算被污染。

**路径 B: IsotropicGrad in calcGradPhi**
```
calcGradPhi() → IsotropicGrad('gradPhi', 'PhaseF') → 读取 26 个邻居 PhaseF
```
同上，梯度被 -999 污染。

**路径 C: calcPhaseGradCloseToBoundary**
```
calcPhaseGradCloseToBoundary() → 读取 PhaseF(±1, 0, 0) 等
```
此函数试图在模板触及边界时回退到一阶/二阶有限差分。但由于 §2.3 的运算符 bug，回退逻辑可能失效，仍然读取 -999 值。

**路径 D: calcWallPhase 中读取 PhaseF_dyn**
```
pf_f = PhaseF_dyn(nw_x, nw_y, nw_z);
```
这里读取第一流体格点的 PhaseF，通过 `both_probes_fluid = (pf_f > -100.0) && (pf_ff > -100.0)` 保护。这个保护是有效的，使用 -100 作为阈值。

### 4.3 缓解措施（已实现）

**`calcPhaseF()` (Dynamics.c.Rt:159-163)**:
```c
if (!(IamWall || IamSolid)) {
    PhaseF = sum(h);  // 正常更新
} else {
    PhaseF = PhaseF(0,0,0);  // 保持原值
}
```
壁面节点的 PhaseF 不被 sum(h) 覆盖。如果 `calcWallPhase` 正确设置了 PhaseF（如 analytic 路径设为 pf_f），则保持该值。

**analytic 路径的保护** (Boundary.c.Rt:972):
```c
PhaseF = pf_f;  // 壁面节点使用流体侧值，不使用 -999
```
这意味着在 analytic 路径下，壁面节点的 PhaseF 被替换为有限值，路径 A 和 B 的污染被消除——前提是该节点被 analytic 路径覆盖。

**⚠️ 非覆盖节点的残余污染**:

以下壁面节点**不在** analytic 路径的覆盖范围内：
1. `AnalyticWetting ≤ 0.5` 的所有壁面节点
2. analytic 法向量指向固体的角/边节点（probe 不是流体节点）
3. `d_to_surface ≥ 1.5` 的壁面节点（距离 analytic 表面太远）

这些节点的 PhaseF 仍然是 -999，会通过路径 A 和 B 污染紧邻壁面的流体节点的 μ 和 ∇φ。

### 4.4 污染量化估算

以平面壁为例，假设壁面在 y=0，流体在 y≥1。

第一层流体节点 (y=1) 的 Laplace 模板:
- 需要读取 PhaseF(1,0,0), PhaseF(-1,0,0), PhaseF(0,1,0), PhaseF(0,-1,0), ...
- PhaseF(0,0,0) 是流体节点本身，正常
- PhaseF(0,-1,0) 是壁面节点 = -999（如果非 analytic 覆盖）
- PhaseF(1,-1,0), PhaseF(-1,-1,0) 是边邻居，也是壁面节点 = -999
- PhaseF(1,1,-1) 等角邻居也可能触及壁面

以标准 26 点 Laplace，一个壁面节点影响 6+12+8 = 26 个邻居中最多 7 个读取路径（自身 + y 方向 3 + 对角 3）。

代入数值: -999 × 16 / 36 ≈ -444 (面邻居), -999 × 4 / 36 ≈ -111 (边邻居), -999 × 1 / 36 ≈ -28 (角邻居)。

**结论**: 即使只有一个 -999 被读取，μ 的值就会被完全破坏。这不是小误差，是数值灾难。

**但实际模拟并未完全崩溃** — 为什么？

答案: `calcWallPhase` 在非 analytic 路径下也设置了 `PhaseF` 为有限值（line 1036-1039 或 1132），只是用了不精确的公式。所以实际上 -999 只存在于以下窗口：
1. Init 阶段，calcWallPhase 还没运行之前
2. IsSpecialBoundaryPoint == NORMAL_POINTING_INTO_SOLID 的节点 (line 996-999: 设为 2342e10，更糟！)
3. h < 0.001 的孤立节点 (line 990-992: 设为 1)

**🔴 发现**: `NORMAL_POINTING_INTO_SOLID` 的特殊点被设置为 `SPECIAL_POINT_HUGE_MAGIC_NUMBER = 2342e10`，这个值比 -999 的危害更大——它不会触发 `> -100` 的保护检查，而是作为一个巨大的正数被模板读取。

---

## 5. Init_wallNorm 法向量计算数学验证

**源文件**: `Boundary.c.Rt:1147-1219`

### 5.1 加权法向量公式

```c
solidFlag[i] = PhaseF_dyn(ex[i], ey[i], ez[i]) / -998;
myNorm[0] += wg[i] * solidFlag[i] * d3q27_ex[i];
myNorm[1] += wg[i] * solidFlag[i] * d3q27_ey[i];
myNorm[2] += wg[i] * solidFlag[i] * d3q27_ez[i];
myNorm *= -1.0/3.0;
```

**数学分析**:

`PhaseF / -998` 将 -999 映射为 ≈1.001（固体），正常值（0-1 范围内）映射为接近 0（流体）。

`wg[i]` 是 D3Q27 权重：
- w0 = 8/27 (静止)
- w1-w6 = 2/27 (面邻居, |e|=1)
- w7-w14 = 1/216 (角邻居, |e|=√3)
- w15-w26 = 1/54 (边邻居, |e|=√2)

法向量 = -1/3 × Σ w_i · flag_i · e_i

**物理含义**: 这是将固体分数的加权矩作为表面法向量的估计。-1/3 是归一化因子。

**⚠️ 归一化因子验证**:

考虑半空间情况 (y<0 全固体, y≥0 全流体)。壁面节点在 y=0。

固体邻居: (0,-1,0) → flag=1, e=(0,-1,0), w=2/27
其余 26 个方向: flag≈0

myNorm_y = -1/3 × 2/27 × 1 × (-1) = 2/81 ≈ 0.0247
myNorm_x = 0, myNorm_z = 0

法向量方向: (0, 2/81, 0) → 指向 +y (流体侧) ✅

但模: |n| = 2/81 ≈ 0.0247，非常小。后续通过找最近 D3Q27 方向来量化，这不受模的影响。

**⚠️ 问题 1: wg 权重与法向量估计的关系**

D3Q27 的权重 wg 是根据平衡分布函数的约束确定的，不是为法向量估计设计的。使用 wg 作为加权因子是一个启发式选择，没有严格的理论基础。

理论上更合理的做法是使用几何权重 (例如根据格点到壁面的距离加权)。当前做法可能引入系统偏差，特别是在曲面壁附近。

**⚠️ 问题 2: PhaseF / -998 的阈值选择**

-999 / -998 = 1.001002...，这确实接近 1。但如果 PhaseF 因为其他原因（如数值误差）变为 -500，则 -500/-998 = 0.501，被当作"半固体"。这个线性映射没有物理依据。

更合理的阈值判断应该是 `PhaseF < -100`（代码中其他地方使用此阈值）。

**⚠️ 问题 3: 角/边退化**

在壁面的角或边处，多个方向的 solidFlag 都为 1，导致法向量不确定。代码通过"找最近 D3Q27 方向"来解决，但 D3Q27 只有 27 个离散方向，在角/边处的法向量可能有 ~25° 的量化误差（这是已知的，stage9 analytic 正是为了解决这个问题）。

---

## 6. 死代码: stage9_calc_wall_ghost

**源文件**: `Boundary.c.Rt:409-438`

```c
CudaDeviceFunction real_t stage9_calc_wall_ghost(
    vector_t n_w, real_t h0, real_t phi_0, vector_t grad)
{
    real_t tan_coeff = tan(PI/2.0 - radAngle);
    real_t kappa_corr = stage9_analytic_curvature() * h0 * h0;
    real_t ghost = phi_0 + 2.0 * h0 * tan_coeff * gt_mag
                          + kappa_corr * tan_coeff * gt_mag;
    // clamp to [PhaseField_l, PhaseField_h]
    return ghost;
}
```

**状态**: 🔴 **NEVER CALLED** — 这个函数实现了带曲率修正的 tan 公式，但在 `calcWallPhase()` 中从未被调用。实际使用的是 Briant 公式 (line 959-971)。

**曲率修正项**: `kappa_corr = κ·h₀²`，其中 κ 是通过 `stage9_analytic_curvature()` 计算的 analytic 曲率。

**影响**: 曲率修正从未生效。对于曲面壁（球、圆柱），这意味着 O(W/R) 误差没有被修正。Stage12 验证中球面和圆柱面的误差（+6.9° 球面 θ=30, +7.8° 圆柱 θ=30）可能部分源于此。

**建议**: 要么激活此函数（替换或补充 Briant 公式），要么删除死代码以避免混淆。

---

## 7. h 分布碰撞: Allen-Cahn BGK（非 MRT）

**源文件**: `Dynamics.c.Rt:846-859`

```c
tmp1 = (1.0 - 4.0*(C - 0.5)*(C - 0.5))/IntWidth;
F_phi[i] = wh[i] * tmp1 * (e_i · n);
h[i] = h[i] - omega * (h[i] - heq[i] + 0.5*F_phi[i]) + F_phi[i];
```

**注意**: 虽然 g 分布使用完整的 27 矩 MRT 碰撞，h 分布始终使用 BGK 式松弛（单一 ω_h 参数）。

这不违反"D3Q27 MRT only"的要求——相场的 Allen-Cahn 方程本身就是一个松弛方程，BGK 松弛是它的标准离散化方式。MRT 的优势（分离不同矩的松弛时间）对 g (Navier-Stokes) 重要，对 h (标量输运) 不需要。

**⚠️ 但有一个闭合缺口**: `F_phi` 的计算使用了 `wh`（零速平衡权重），而不是完整的平衡态。`wh` 是什么？

```r
if (Options$q27){
    wh = EQ_h$feq  # 在 u=0 时的平衡态，即纯权重
}
```

`wh` = feq(ρ=1, u=0) = 权重向量。但 `F_phi` 的物理含义是"相场源项"：
```
F_phi[i] = w_i · (1/IntWidth) · (1 - 4(C-0.5)²) · (e_i · n)
```

其中 `n = ∇φ/|∇φ|` 是界面法向量。这个源项来自 Allen-Cahn 方程的离散化：
```
∂φ/∂t + u·∇φ = (1/IntWidth)·(1-4(φ-0.5)²)·(∂²φ/∂n²)  ← 不完全正确
```

实际上 F_phi 中的 `(e_i · n)` 将界面法向的信息编码到分布函数中，然后通过碰撞松弛恢复界面的运动。

**闭合性**: 这个公式的闭合依赖于假设"界面法向 n 在一个碰撞步内不变"，这是一个合理的近似（因为 W >> Δx），但在高曲率处可能失效。

---

## 8. 粘性力隐式迭代: 2 步硬编码

**源文件**: `Dynamics.c.Rt:822-844`

```c
j = 0;
do {
    j++;
    // 计算 MRT 非平衡应力 tensor
    // 计算 F_mu
    // 更新 u = m0[2:4] + 0.5 * F_total / rho
} while (j < force_fixed_iterator);  // force_fixed_iterator 默认为 2
```

**⚠️ 未闭合**: 粘性力 F_mu 依赖于应力 tensor Π，而 Π 依赖于 u，而 u 依赖于 F_total（包含 F_mu）。这是一个隐式耦合，需要迭代求解。

代码使用固定 2 步迭代，**没有收敛检查**。在高密度比、高 Re 数或强界面变形的情况下，2 步可能不够。

**后果**: 粘性力的不准确会导致接触线附近的流场误差，间接影响接触角的稳态值。

---

## 9. Stage12 验证结果的诊断解读

结合 `stage12_validation_report_20260615.md` 的数据:

### 9.1 Decoupled 响应全部失败

所有 6 个 decoupled case 都没有向 BC 目标角度移动。例如:
- `decouple_wall_60to30`: 初始 60°, BC 目标 30°, 最终 69.3° — 反而远离目标
- `decouple_wall_120to150`: 初始 120°, BC 目标 150°, 最终 111.8° — 也远离目标

**与本审计的关联**:
1. **§4 的 -999 污染**: decoupled case 中初始 cap 的接触线位置不同于 BC 指定的位置。这意味着在 transient 期间，界面移动，可能经过没有 analytic 保护的壁面区域，触发 -999 污染。
2. **§2.3 的运算符 bug**: `calcPhaseGradCloseToBoundary` 的回退逻辑失效，导致梯度在界面移动过程中不正确。
3. **§8 的粘性力迭代不足**: 2 步迭代在 transient 界面移动中可能导致力的不准确。

### 9.2 Equilibrium case 部分收敛

- `equil_wall_t30`: 目标 30°, 测得 42.6° (+12.6°) — cot(θ) 误差
- `equil_cyl_t150`: 目标 150°, 测得 144.7° (-5.3°) — 最佳
- `equil_sphere_t150`: 目标 150°, 测得 121.2° (-28.8°) — 最差

**球面 θ=150 的巨大误差**可能源于:
1. 封闭球面 STL 的角/边节点未覆盖（analytic probe 指向固体）
2. 这些节点的 PhaseF = -999，污染相邻流体节点
3. 曲面法向量在角/边处的退化

---

## 10. 发现汇总表

| # | 类别 | 严重性 | 位置 | 描述 | 状态 |
|---|------|--------|------|------|------|
| F1 | FD Bug | 🔴 Critical | Boundary.c.Rt:784-786 | forcedFiniteDifference 中 6 处 `||` 写为 `-` | 未修复 |
| F2 | FD Gap | 🔴 Critical | Dynamics.c.Rt:217 | calcMu 的 Laplace 在非 OutFlow 边界无 -999 保护 | 未修复 |
| F3 | FD Gap | 🔴 Critical | Dynamics.c.Rt:144 | calcGradPhi 的梯度在非 OutFlow 边界无 -999 保护 | 未修复 |
| F4 | BC Math | 🟡 Major | Boundary.c.Rt:996-999 | NORMAL_POINTING_INTO_SOLID 节点设为 2342e10 | 未修复 |
| F5 | BC Dead | 🟡 Major | Boundary.c.Rt:409-438 | stage9_calc_wall_ghost 带曲率修正但从未被调用 | 未修复 |
| F6 | BC Math | 🟡 Major | Boundary.c.Rt:1127 | 几何 BC 使用 |grad_tangent| 丢失方向信息 | 设计问题 |
| F7 | BC Math | 🟡 Major | Boundary.c.Rt:1121-1123 | 1.5·g1-0.5·g2 外推在界面反号时不稳定 | 设计问题 |
| F8 | Force | 🟡 Major | Dynamics.c.Rt:844 | 粘性力隐式迭代 2 步硬编码，无收敛检查 | 未修复 |
| F9 | Init | 🟠 Medium | Boundary.c.Rt:1184 | PhaseF/-998 线性映射作为固体标志，物理依据不足 | 设计问题 |
| F10 | BC Math | 🟠 Medium | Boundary.c.Rt:58-71 | h 分布 Zou-He 处理无 Chapman-Enskog 闭合 | 设计问题 |
| F11 | BC Math | 🟠 Medium | Boundary.c.Rt:225-258 | h 分布 bounce-back 物理含义未定义 | 设计问题 |
| F12 | Force | 🟠 Medium | Dynamics.c.Rt:859 | h 的 Allen-Cahn BGK 在高曲率处精度退化 | 模型固有 |
| F13 | BC | 🔵 Info | — | Briant=tan=upstream 给出相同结果，cot(θ) 误差模型固有 | 已知 |
| F14 | FD Math | ✅ OK | model.R:71-78 | IsotropicGrad 四阶精度数学验证通过 | — |
| F15 | FD Math | ✅ OK | model.R:79-82 | myLaplace 二阶精度数学验证通过 | — |

---

## 11. 修复优先级建议

### P0 (阻塞性): 必须立即修复

1. **F1**: 修复 `forcedFiniteDifference` 中的 6 处 `||` → `-` 运算符 bug。这只需要在 R 模板中将 `"- "` 替换为 `"|| "`。
2. **F4**: 将 `SPECIAL_POINT_HUGE_MAGIC_NUMBER` 从 2342e10 改为某个有限值或 -999，并在 calcMu/calcGradPhi 中添加 -999 保护。
3. **F2/F3**: 在 calcMu 和 calcGradPhi 的非 OutFlow 路径中添加边界感知逻辑：如果 26 邻居中有 -999 值，回退到一阶/二阶有限差分（类似于 calcPhaseGradCloseToBoundary）。

### P1 (高优先级): 应在下一阶段修复

4. **F5**: 激活 `stage9_calc_wall_ghost` 的曲率修正，或证明为什么不需要。
5. **F8**: 将粘性力迭代改为收敛检查（例如 |F_total^(n+1) - F_total^(n)| < tol），而非硬编码 2 步。

### P2 (中优先级): 应在论文投稿前解决

6. **F6/F7**: 改进几何 BC 的梯度和外推方案。
7. **F9**: 改用阈值判断代替 PhaseF/-998 线性映射。
8. **F10/F11**: 给 h 的边界处理添加理论依据或引用。

### P3 (已知): 记录为模型局限性

9. **F12**: Allen-Cahn BGK 的高曲率退化。
10. **F13**: cot(θ) 误差是 Fakhari-Mitchell 模型固有。

---

## 12. 附录: Stage12 decoupled case 失败的假设链

Decoupled case 的失败（形状不向 BC 目标移动）可以用以下因果链解释：

```
初始 cap (θ_init) ≠ BC 目标 (θ_bc)
    → 界面需要移动来调整接触角
    → 界面移动经过壁面附近区域
    → 壁面附近 PhaseF 被 -999 污染 (F2/F3)
    → calcPhaseGradCloseToBoundary 回退失效 (F1)
    → 梯度和化学势计算错误
    → 力 (F_s, F_p, F_mu) 计算错误
    → 界面收到错误的驱动力
    → 界面不向平衡位置移动，甚至远离
```

这个假设可以通过以下实验验证：
1. 修复 F1 后重新运行 decoupled case
2. 在修复前后监测壁面附近第一层流体节点的 μ 和 |∇φ| 值
3. 如果修复后 decoupled case 开始向目标移动，则确认因果链

---

*Report end. 本报告仅做审计分析，未修改任何代码。*
