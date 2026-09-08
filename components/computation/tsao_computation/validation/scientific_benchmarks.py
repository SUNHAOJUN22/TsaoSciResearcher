from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkResult:
    benchmark_id: str
    domain: str
    observed: float
    expected: float
    absolute_error: float
    relative_error: float
    tolerance: float
    passed: bool
    invariant: str

    def to_dict(self) -> dict[str, float | str | bool]:
        return asdict(self)


def assess(
    benchmark_id: str,
    domain: str,
    observed: float,
    expected: float,
    tolerance: float,
    invariant: str,
) -> BenchmarkResult:
    values = (observed, expected, tolerance)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("benchmark values and tolerance must be finite")
    if tolerance < 0:
        raise ValueError("benchmark tolerance must be non-negative")
    try:
        absolute_error = abs(math.fsum((observed, -expected)))
    except OverflowError as error:
        raise ValueError("benchmark error overflowed finite arithmetic") from error
    if not math.isfinite(absolute_error):
        raise ValueError("benchmark absolute error is not finite")
    if expected == 0.0:
        relative_error = absolute_error
        passed = absolute_error <= tolerance
    else:
        relative_error = absolute_error / abs(expected)
        if not math.isfinite(relative_error):
            raise ValueError("benchmark relative error is not finite")
        passed = relative_error <= tolerance
    return BenchmarkResult(
        benchmark_id=benchmark_id,
        domain=domain,
        observed=observed,
        expected=expected,
        absolute_error=absolute_error,
        relative_error=relative_error,
        tolerance=tolerance,
        passed=passed,
        invariant=invariant,
    )


def steady_conduction() -> BenchmarkResult:
    nodes = 41
    left, right = 350.0, 300.0
    dx = 1.0 / (nodes - 1)
    interior = nodes - 2
    lower = [-1.0] * (interior - 1)
    diagonal = [2.0] * interior
    upper = [-1.0] * (interior - 1)
    rhs = [0.0] * interior
    rhs[0], rhs[-1] = left, right
    for index in range(1, interior):
        factor = lower[index - 1] / diagonal[index - 1]
        diagonal[index] -= factor * upper[index - 1]
        rhs[index] -= factor * rhs[index - 1]
    solution = [0.0] * interior
    solution[-1] = rhs[-1] / diagonal[-1]
    for index in range(interior - 2, -1, -1):
        solution[index] = (rhs[index] - upper[index] * solution[index + 1]) / diagonal[index]
    temperatures = [left, *solution, right]
    maximum_error = max(
        abs(value - (left + (right - left) * index * dx))
        for index, value in enumerate(temperatures)
    )
    return assess(
        "steady-conduction-1d",
        "heat-transfer",
        maximum_error,
        0.0,
        1.0e-11,
        "finite-difference profile matches the linear analytical solution",
    )


def poiseuille_flow() -> BenchmarkResult:
    radius, pressure_drop, viscosity, length = 0.01, 100.0, 1.0e-3, 1.0
    intervals = 4000
    dr = radius / intervals
    velocity_scale = pressure_drop / (4.0 * viscosity * length)
    radius_squared = radius * radius

    integral = 0.0
    for index in range(intervals + 1):
        radial_position = index * dr
        weight = 0.5 if index in (0, intervals) else 1.0
        velocity = velocity_scale * (radius_squared - radial_position * radial_position)
        integral += weight * velocity * radial_position
    numerical_flow = 2.0 * math.pi * integral * dr
    analytical_flow = math.pi * pressure_drop * radius**4 / (8.0 * viscosity * length)
    return assess(
        "poiseuille-pipe-flow",
        "fluid-dynamics",
        numerical_flow,
        analytical_flow,
        2.0e-7,
        "integrated parabolic profile matches Hagen-Poiseuille flow",
    )


def cstr_mass_balance() -> BenchmarkResult:
    concentration_in, rate_constant, residence_time = 2.0, 0.4, 3.0
    concentration_out = concentration_in / (1.0 + rate_constant * residence_time)
    residual = (concentration_in - concentration_out) / residence_time
    residual -= rate_constant * concentration_out
    return assess(
        "cstr-first-order-balance",
        "reaction-engineering",
        residual,
        0.0,
        1.0e-14,
        "steady inlet-outlet-generation mass balance closes",
    )


def pfr_first_order() -> BenchmarkResult:
    rate_constant, residence_time, steps = 0.7, 2.0, 1000
    step = residence_time / steps
    concentration = 1.0
    half_step = 0.5 * step
    sixth_step = step / 6.0

    for _ in range(steps):
        k1 = -rate_constant * concentration
        k2 = -rate_constant * (concentration + half_step * k1)
        k3 = -rate_constant * (concentration + half_step * k2)
        k4 = -rate_constant * (concentration + step * k3)
        concentration += sixth_step * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    return assess(
        "pfr-first-order-rk4",
        "reaction-engineering",
        concentration,
        math.exp(-rate_constant * residence_time),
        1.0e-11,
        "RK4 plug-flow integration matches analytical first-order decay",
    )


def harmonic_oscillator() -> BenchmarkResult:
    time_step, steps = 0.002, 5000
    position, velocity, acceleration = 1.0, 0.0, -1.0
    initial_energy, maximum_drift = 0.5, 0.0
    half_time_step = 0.5 * time_step
    half_time_step_squared = half_time_step * time_step
    for _ in range(steps):
        position += velocity * time_step + acceleration * half_time_step_squared
        next_acceleration = -position
        velocity += (acceleration + next_acceleration) * half_time_step
        acceleration = next_acceleration
        energy = 0.5 * (position**2 + velocity**2)
        maximum_drift = max(maximum_drift, abs(energy - initial_energy) / initial_energy)
    return assess(
        "harmonic-oscillator-verlet",
        "molecular-dynamics",
        maximum_drift,
        0.0,
        1.1e-6,
        "velocity-Verlet bounds total-energy drift",
    )


def gaussian_chain() -> BenchmarkResult:
    segments, segment_length = 120.0, 0.154
    covariance_trace = 3.0 * (segments * segment_length**2 / 3.0)
    return assess(
        "gaussian-chain-second-moment",
        "polymer-statistical-mechanics",
        covariance_trace,
        segments * segment_length**2,
        1.0e-14,
        "isotropic covariance trace equals N b^2",
    )


def parallel_plate_capacitor() -> BenchmarkResult:
    voltage, spacing, nodes = 1000.0, 0.01, 101
    dx = spacing / (nodes - 1)
    potentials = [voltage * index / (nodes - 1) for index in range(nodes)]
    fields = [
        -(potentials[index + 1] - potentials[index - 1]) / (2.0 * dx)
        for index in range(1, nodes - 1)
    ]
    mean_magnitude = sum(abs(field) for field in fields) / len(fields)
    return assess(
        "parallel-plate-electric-field",
        "electrostatics",
        mean_magnitude,
        voltage / spacing,
        1.0e-14,
        "central-difference electric field matches V/d",
    )


def electrothermal_balance() -> BenchmarkResult:
    voltage, resistance, conductance = 24.0, 12.0, 0.8
    current = voltage / resistance
    electrical_power = voltage * current
    joule_power = current**2 * resistance
    temperature_rise = joule_power / conductance
    removed_heat = conductance * temperature_rise
    mismatch = max(abs(electrical_power - joule_power), abs(joule_power - removed_heat))
    return assess(
        "electrothermal-steady-balance",
        "multiphysics",
        mismatch,
        0.0,
        1.0e-14,
        "electrical input, Joule heating, and steady heat removal close",
    )


BENCHMARKS: tuple[Callable[[], BenchmarkResult], ...] = (
    steady_conduction,
    poiseuille_flow,
    cstr_mass_balance,
    pfr_first_order,
    harmonic_oscillator,
    gaussian_chain,
    parallel_plate_capacitor,
    electrothermal_balance,
)


def run_all() -> list[BenchmarkResult]:
    results = [benchmark() for benchmark in BENCHMARKS]
    identifiers = [result.benchmark_id for result in results]
    if len(identifiers) != len(set(identifiers)):
        raise RuntimeError("scientific benchmark identifiers must be unique")
    return results


def write_report(path: Path) -> dict[str, object]:
    results = run_all()
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "claim_boundary": (
            "Deterministic analytical, conservation, and invariant benchmarks; "
            "no third-party solver execution is claimed."
        ),
        "total": len(results),
        "passed": sum(result.passed for result in results),
        "failed": sum(not result.passed for result in results),
        "results": [result.to_dict() for result in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return payload
