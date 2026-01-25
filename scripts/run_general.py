#!/usr/bin/env python3
"""
Utility to batch-run all general Sudoku instances through the ACS solver.

Example:
    python scripts/run_general.py --verbose
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess, run, PIPE
from typing import Iterable, List, Optional, Sequence, Tuple, Dict


@dataclass(frozen=True)
class InstanceMetadata:
    path: Path
    size_label: str
    fixed_percentage: Optional[int]
    instance_id: Optional[int]

    @property
    def relative_path(self) -> str:
        repo_root = find_repo_root()
        return str(self.path.relative_to(repo_root))


def find_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_solver_candidates() -> Sequence[str]:
    if os.name == "nt":
        return (
            "sudoku_ants.exe",
            "sudoku_ants",
            os.path.join("vs2017", "x64", "Release", "sudoku_ants.exe"),
            os.path.join("vs2017", "Release", "sudoku_ants.exe"),
        )
    return (
        "./sudoku_ants",
        "sudoku_ants",
        os.path.join("vs2017", "x64", "Release", "sudoku_ants"),
        os.path.join("vs2017", "Release", "sudoku_ants"),
    )


def resolve_solver_path(user_value: Optional[str]) -> Path:
    repo_root = find_repo_root()
    if user_value:
        solver_path = Path(user_value)
        if not solver_path.is_absolute():
            solver_path = (repo_root / solver_path).resolve()
        if solver_path.exists():
            return solver_path
        raise FileNotFoundError(f"Solver binary not found at '{solver_path}'.")

    for candidate in default_solver_candidates():
        candidate_path = (repo_root / candidate).resolve()
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path

    raise FileNotFoundError(
        "Solver binary not found. Build it first (e.g. run `make -f Makefile`)."
    )


def natural_sort_key(path: Path) -> list:
    """
    Generate a sort key that handles numeric parts naturally.
    E.g., '9x9hard_2' comes before '9x9hard_10'
    """
    import re
    parts = []
    for part in re.split(r'(\d+)', path.name):
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(part)
    return parts


def iter_instance_files(instances_root: Path) -> Iterable[Path]:
    if not instances_root.exists():
        raise FileNotFoundError(f"Instances folder not found: '{instances_root}'.")
    # Find all .txt files and files without extensions (for "hard" folder)
    all_files = list(instances_root.glob("*.txt"))
    # Also include files without extensions (filter out directories)
    all_files.extend([f for f in instances_root.glob("*") if f.is_file() and f.suffix == ""])
    # Sort naturally so 9x9hard_1, 9x9hard_2, ... 9x9hard_10 are in correct order
    return sorted(all_files, key=natural_sort_key)


def iter_all_instance_files(repo_root: Path) -> Iterable[Path]:
    """Iterate over both general and logic-solvable instances."""
    all_files = []
    
    # General instances
    general_root = repo_root / "instances" / "general"
    if general_root.exists():
        all_files.extend(general_root.glob("*.txt"))
    
    # Logic-solvable instances
    logic_root = repo_root / "instances" / "logic-solvable"
    if logic_root.exists():
        all_files.extend(logic_root.glob("*.txt"))
    
    if not all_files:
        raise FileNotFoundError("No instance files found in 'instances/general' or 'instances/logic-solvable'.")
    
    return sorted(all_files)


def parse_metadata(path: Path) -> InstanceMetadata:
    name = path.stem
    match = re.match(r"inst(?P<size>[0-9x]+)_(?P<fixed>\d+)_(?P<idx>\d+)", name)
    size = None
    fixed = None
    idx = None
    if match:
        size = match.group("size")
        fixed = int(match.group("fixed"))
        idx = int(match.group("idx"))
    else:
        # Logic-solvable instances: use puzzle name as size_label
        size = name
    return InstanceMetadata(path=path, size_label=size or "unknown", fixed_percentage=fixed, instance_id=idx)


def sort_instance_metadata(instances: Sequence[InstanceMetadata]) -> List[InstanceMetadata]:
    size_order = {"9x9": 0, "16x16": 1, "25x25": 2, "36x36": 3}

    def key(meta: InstanceMetadata) -> Tuple[int, int, int, list]:
        return (
            size_order.get(meta.size_label, 99),
            meta.fixed_percentage if meta.fixed_percentage is not None else 999,
            meta.instance_id if meta.instance_id is not None else 999,
            natural_sort_key(meta.path),
        )

    return sorted(instances, key=key)


def format_instance_argument(instance_path: Path, repo_root: Path) -> str:
    try:
        rel_path = instance_path.relative_to(repo_root)
    except ValueError:
        path_str = str(instance_path)
    else:
        prefixed = Path(".") / rel_path
        path_str = str(prefixed)
    
    # Quote paths with spaces (for Windows compatibility)
    if ' ' in path_str:
        return f'"{path_str}"'
    return path_str


def build_solver_command(
    solver_path: Path,
    instance_path: Path,
    repo_root: Path,
    args: argparse.Namespace,
    algorithm: int,
) -> List[str]:
    file_arg = format_instance_argument(instance_path, repo_root)
    cmd: List[str] = [str(solver_path), "--file", file_arg, "--alg", str(algorithm), "--timeout", str(args.timeout)]

    # Determine ant count based on algorithm
    # Algorithms 0 and 2: use --ants-single if specified, else --ants
    # Algorithms 3 and 4: use --ants-multi if specified, else --ants
    ant_count = None
    if algorithm in [0, 2]:
        ant_count = args.ants_single if args.ants_single is not None else args.ants
    elif algorithm in [3, 4]:
        ant_count = args.ants_multi if args.ants_multi is not None else args.ants
    
    if ant_count is not None:
        cmd.extend(("--ants", str(ant_count)))
    if args.subcolonies is not None:
        cmd.extend(("--subcolonies", str(args.subcolonies)))
    if args.threads is not None:
        cmd.extend(("--threads", str(args.threads)))
    if args.numcolonies is not None:
        cmd.extend(("--numcolonies", str(args.numcolonies)))
    if args.numacs is not None:
        cmd.extend(("--numacs", str(args.numacs)))
    if args.q0 is not None:
        cmd.extend(("--q0", str(args.q0)))
    if args.rho is not None:
        cmd.extend(("--rho", str(args.rho)))
    if args.evap is not None:
        cmd.extend(("--evap", str(args.evap)))
    # Always add verbose for algorithms 0, 2, 3, and 4 to get iteration count and timing info
    if algorithm == 0 or algorithm == 2 or algorithm == 3 or algorithm == 4 or args.solver_verbose:
        cmd.append("--verbose")
    return cmd


def run_solver(cmd: Sequence[str], cwd: Path, timeout: Optional[float], show_progress: bool = False) -> CompletedProcess:
    if show_progress:
        # Don't capture stderr so progress messages show in real-time
        return run(
            list(cmd),
            cwd=str(cwd),
            stdout=PIPE,
            stderr=None,  # Let stderr go directly to console
            text=True,
            timeout=timeout,
        )
    else:
        return run(
            list(cmd),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )


def parse_solver_output(stdout: str, stderr: str) -> Tuple[Optional[bool], Optional[float], Optional[int], Optional[bool], Optional[float], Optional[float], Optional[int], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], str, str]:
    stdout_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    stderr_lines = [line.strip() for line in stderr.splitlines() if line.strip()]

    success: Optional[bool] = None
    solve_time: Optional[float] = None
    iterations: Optional[int] = None
    communication: Optional[bool] = None
    cp_initial: Optional[float] = None
    cp_ant: Optional[float] = None
    cp_calls: Optional[int] = None
    # New timing fields
    acs_time: Optional[float] = None  # For algorithms 0, 2
    dcm_aco_time: Optional[float] = None  # For algorithms 3, 4
    coop_game_time: Optional[float] = None
    pheromone_fusion_time: Optional[float] = None
    public_path_time: Optional[float] = None
    communication_time: Optional[float] = None

    # Combine stdout and stderr for parsing (iterations might be in either)
    all_lines = stdout_lines + stderr_lines

    for line in all_lines:
        if line in {"0", "1"} and success is None:
            success = (line == "0")
            continue

        solved_match = re.search(r"[Ss]olved in ([0-9]*\.?[0-9]+)", line)
        if solved_match:
            solve_time = float(solved_match.group(1))
            success = True
            continue

        # Match both old format "failed in time X" and new format "Failed to solve in X seconds"
        failed_match = re.search(r"[Ff]ailed (?:in time |to solve in )([0-9]*\.?[0-9]+)", line)
        if failed_match:
            solve_time = float(failed_match.group(1))
            success = False
            continue

        # Parse iterations (for algorithms 0, 2, 3, 4)
        # Match both "iterations:" and "Iterations:"
        iter_match = re.search(r"[Ii]terations:\s*([0-9]+)", line)
        if iter_match:
            iterations = int(iter_match.group(1))
            continue

        # Parse communication flag for algorithms 2 and 4
        # Match both "communication:" and "Communication:"
        comm_match = re.search(r"[Cc]ommunication:\s*(yes|no)", line, re.IGNORECASE)
        if comm_match:
            communication = (comm_match.group(1).lower() == "yes")
            continue
        
        # Parse CP timing data (legacy format)
        cp_initial_match = re.search(r"cp_initial:\s*([0-9]*\.?[0-9]+)", line)
        if cp_initial_match:
            cp_initial = float(cp_initial_match.group(1))
            continue
        
        cp_ant_match = re.search(r"cp_ant:\s*([0-9]*\.?[0-9]+)", line)
        if cp_ant_match:
            cp_ant = float(cp_ant_match.group(1))
            continue
        
        cp_calls_match = re.search(r"cp_calls:\s*([0-9]+)", line)
        if cp_calls_match:
            cp_calls = int(cp_calls_match.group(1))
            continue
        
        # Parse new timing fields from verbose output (==Time Breakdown== section)
        # Format: "Initial CP Time: X s (Y%)"
        initial_cp_match = re.search(r"Initial CP Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
        if initial_cp_match:
            cp_initial = float(initial_cp_match.group(1))
            continue
        
        # Format: "Ant CP Time: X s (Y%)"
        ant_cp_match = re.search(r"Ant CP Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
        if ant_cp_match:
            cp_ant = float(ant_cp_match.group(1))
            continue
        
        # Format: "ACS Time: X s (Y%)" (for algorithms 0, 2)
        acs_time_match = re.search(r"ACS Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
        if acs_time_match:
            acs_time = float(acs_time_match.group(1))
            continue
        
        # Format: "DCM-ACO Time: X s (Y%)" (for algorithms 3, 4)
        dcm_aco_time_match = re.search(r"DCM-ACO Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
        if dcm_aco_time_match:
            dcm_aco_time = float(dcm_aco_time_match.group(1))
            continue
        
        # Format: "Cooperative Game Time: X s (Y%)" (full name, not abbreviated)
        coop_game_match = re.search(r"Cooperative Game Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
        if coop_game_match:
            coop_game_time = float(coop_game_match.group(1))
            continue
        
        # Format: "Pheromone Fusion Time: X s (Y%)"
        fusion_match = re.search(r"Pheromone Fusion Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
        if fusion_match:
            pheromone_fusion_time = float(fusion_match.group(1))
            continue
        
        # Format: "Public Path Recommendation Time: X s (Y%)" (full name)
        public_path_match = re.search(r"Public Path Recommendation Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
        if public_path_match:
            public_path_time = float(public_path_match.group(1))
            continue
        
        # Format: "Communication Between Threads Time: X s (Y%)"
        comm_time_match = re.search(r"Communication Between Threads Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
        if comm_time_match:
            communication_time = float(comm_time_match.group(1))
            continue
        
        # Format: "Total Solve Time: X s"
        total_time_match = re.search(r"Total Solve Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
        if total_time_match:
            solve_time = float(total_time_match.group(1))
            continue

    # Fallback: check stdout for time if not found yet
    for line in stdout_lines:
        # Fallback: if a line can be parsed as float and we still do not have a time.
        if solve_time is None:
            try:
                solve_time = float(line)
            except ValueError:
                pass

    if success is None:
        # Check stderr for clues
        for line in stderr_lines:
            if "could not open file" in line.lower():
                success = False
                break

    if solve_time is not None:
        solve_time = round(solve_time, 5)

    return success, solve_time, iterations, communication, cp_initial, cp_ant, cp_calls, acs_time, dcm_aco_time, coop_game_time, pheromone_fusion_time, public_path_time, communication_time, "\n".join(stdout_lines), "\n".join(stderr_lines)


def get_value_for_alg(alg: int, field: str, value) -> str:
    """Return 'N/A' if field doesn't apply to algorithm, otherwise return value."""
    na_rules = {
        'threads': [0, 1, 3],  # N/A for these algs
        'numcolonies': [0, 1, 2],
        'numacs': [0, 1, 2],
        'acs_time_mean': [1, 3, 4],  # ACS time only for alg 0, 2
        'acs_time_percentage': [1, 3, 4],
        'dcm_aco_time_mean': [0, 1, 2],  # DCM-ACO time only for alg 3, 4
        'dcm_aco_time_percentage': [0, 1, 2],
        'coop_game_mean': [0, 1, 2],
        'coop_game_percentage': [0, 1, 2],
        'pheromone_fusion_mean': [0, 1, 2],
        'pheromone_fusion_percentage': [0, 1, 2],
        'public_path_mean': [0, 1, 2],
        'public_path_percentage': [0, 1, 2],
        'communication_time_mean': [0, 1, 3],
        'communication_time_percentage': [0, 1, 3],
        'with_comm': [0, 1, 3],
        'without_comm': [0, 1, 3],
    }
    if field in na_rules and alg in na_rules[field]:
        return "N/A"
    return value if value != "" else "N/A"


def write_csv(output_path: Path, rows: Sequence[dict], algorithms_run: List[int]) -> None:
    """Write results to CSV with algorithm-specific columns grouped by metric."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build dynamic fieldnames based on algorithms run
    # Group by metric instead of by algorithm for easier comparison in Excel
    # Time components are paired with their percentages for easy comparison
    fieldnames = ["puzzle_size"]
    
    # List of all metrics in desired order
    # Time means listed first, then all percentages grouped at the end for easy summing
    metrics = [
        "nAnts",
        "threads",
        "numcolonies",
        "numacs",
        "q0",
        "rho",
        "bve",
        "timeout",
        "success_rate",
        "time_mean",
        "time_std",
        "iter_mean",
        "with_comm",
        "without_comm",
        # All time means together
        "cp_initial_mean",
        "cp_ant_mean",
        "cp_total_mean",
        "acs_time_mean",  # Main algorithm time for alg 0, 2 (calculated by subtraction)
        "dcm_aco_time_mean",  # Main algorithm time for alg 3, 4 (calculated by subtraction)
        "coop_game_mean",  # Sub-component of DCM-ACO (alg 3, 4)
        "pheromone_fusion_mean",  # Sub-component of DCM-ACO (alg 3, 4)
        "public_path_mean",  # Sub-component of DCM-ACO (alg 3, 4)
        "communication_time_mean",  # For alg 2, 4
        # All percentages grouped at the end for easy summing
        "cp_percentage",
        "acs_time_percentage",  # Percentage for ACS time (alg 0, 2)
        "dcm_aco_time_percentage",  # Percentage for DCM-ACO time (alg 3, 4)
        "coop_game_percentage",  # Sub-component percentage
        "pheromone_fusion_percentage",  # Sub-component percentage
        "public_path_percentage",  # Sub-component percentage
        "communication_time_percentage",  # For alg 2, 4
    ]
    
    # For each metric, add columns for all algorithms
    for metric in metrics:
        for alg in sorted(algorithms_run):
            fieldnames.append(f"{metric}_alg{alg}")
    
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compute_summary(total: int, successes: int, times: Sequence[float]) -> Tuple[int, int, float]:
    avg_time = sum(times) / len(times) if times else 0.0
    return total, successes, round(avg_time, 5)


def summarize_group(size_label: str, fixed_percentage: Optional[int], stats: dict, args: argparse.Namespace) -> dict:
    total = stats.get("total", 0)
    if total == 0:
        return {}

    successes = stats.get("successes", 0)
    fails = stats.get("fails", 0)
    times = stats.get("times", [])
    iterations = stats.get("iterations", [])
    with_comm = stats.get("with_comm", 0)
    without_comm = stats.get("without_comm", 0)
    cp_initial_list = stats.get("cp_initial", [])
    cp_ant_list = stats.get("cp_ant", [])
    cp_calls_list = stats.get("cp_calls", [])
    # New timing lists
    acs_time_list = stats.get("acs_time", [])
    dcm_aco_time_list = stats.get("dcm_aco_time", [])
    coop_game_list = stats.get("coop_game", [])
    pheromone_fusion_list = stats.get("pheromone_fusion", [])
    public_path_list = stats.get("public_path", [])
    communication_time_list = stats.get("communication_time", [])
    
    success_rate = (successes / total) * 100.0 if total else 0.0
    average_time = round(sum(times) / len(times), 5) if times else 0.0
    time_std = round(statistics.pstdev(times), 5) if len(times) > 1 else 0.0
    average_iter = round(sum(iterations) / len(iterations), 2) if iterations else 0.0
    
    # Calculate CP timing statistics using the correct method:
    # Sum all component times across all runs, sum all total solve times, then calculate percentage
    total_cp_initial = sum(cp_initial_list)
    total_cp_ant = sum(cp_ant_list)
    total_cp_time = total_cp_initial + total_cp_ant
    total_solve_time = sum(times)
    
    avg_cp_initial = round(total_cp_initial / len(cp_initial_list), 6) if cp_initial_list else 0.0
    avg_cp_ant = round(total_cp_ant / len(cp_ant_list), 6) if cp_ant_list else 0.0
    avg_cp_total = avg_cp_initial + avg_cp_ant
    cp_percentage = round((total_cp_time / total_solve_time * 100), 2) if total_solve_time > 0 else 0.0
    
    # Calculate new timing statistics
    total_acs_time = sum(acs_time_list)
    total_dcm_aco_time = sum(dcm_aco_time_list)
    total_coop_game = sum(coop_game_list)
    total_pheromone_fusion = sum(pheromone_fusion_list)
    total_public_path = sum(public_path_list)
    total_communication_time = sum(communication_time_list)
    
    avg_acs_time = round(total_acs_time / len(acs_time_list), 6) if acs_time_list else 0.0
    avg_dcm_aco_time = round(total_dcm_aco_time / len(dcm_aco_time_list), 6) if dcm_aco_time_list else 0.0
    avg_coop_game = round(total_coop_game / len(coop_game_list), 6) if coop_game_list else 0.0
    avg_pheromone_fusion = round(total_pheromone_fusion / len(pheromone_fusion_list), 6) if pheromone_fusion_list else 0.0
    avg_public_path = round(total_public_path / len(public_path_list), 6) if public_path_list else 0.0
    avg_communication_time = round(total_communication_time / len(communication_time_list), 6) if communication_time_list else 0.0
    
    # Calculate percentages relative to total solve time
    acs_time_percentage = round((total_acs_time / total_solve_time * 100), 2) if total_solve_time > 0 else 0.0
    dcm_aco_time_percentage = round((total_dcm_aco_time / total_solve_time * 100), 2) if total_solve_time > 0 else 0.0
    coop_game_percentage = round((total_coop_game / total_solve_time * 100), 2) if total_solve_time > 0 else 0.0
    pheromone_fusion_percentage = round((total_pheromone_fusion / total_solve_time * 100), 2) if total_solve_time > 0 else 0.0
    public_path_percentage = round((total_public_path / total_solve_time * 100), 2) if total_solve_time > 0 else 0.0
    communication_time_percentage = round((total_communication_time / total_solve_time * 100), 2) if total_solve_time > 0 else 0.0

    label = size_label
    if fixed_percentage is not None:
        label = f"{label} @ {fixed_percentage}% fixed"

    # Build summary message
    summary_msg = f"Summary {label}: success={successes}, fail={fails}, success_rate={success_rate:.2f}%, avg_time={average_time:.5f}s"
    
    if iterations:
        summary_msg += f", avg_iter={average_iter:.2f}"
    
    if (args.alg == 2 or args.alg == 4) and (with_comm > 0 or without_comm > 0):
        summary_msg += f", comm={with_comm}/{with_comm + without_comm}"
    
    # Add CP timing to summary
    if cp_initial_list and cp_ant_list:
        summary_msg += f", CP: {avg_cp_total:.6f}s ({cp_percentage:.1f}%)"
    
    # Add detailed timing breakdown if available
    timing_parts = []
    if acs_time_list:
        timing_parts.append(f"ACS={avg_acs_time:.6f}s ({acs_time_percentage:.1f}%)")
    if dcm_aco_time_list:
        timing_parts.append(f"DCM-ACO={avg_dcm_aco_time:.6f}s ({dcm_aco_time_percentage:.1f}%)")
    if coop_game_list:
        timing_parts.append(f"CoopGame={avg_coop_game:.6f}s ({coop_game_percentage:.1f}%)")
    if pheromone_fusion_list:
        timing_parts.append(f"PherFusion={avg_pheromone_fusion:.6f}s ({pheromone_fusion_percentage:.1f}%)")
    if public_path_list:
        timing_parts.append(f"PublicPath={avg_public_path:.6f}s ({public_path_percentage:.1f}%)")
    if communication_time_list:
        timing_parts.append(f"CommTime={avg_communication_time:.6f}s ({communication_time_percentage:.1f}%)")
    
    if timing_parts:
        summary_msg += f" | {' '.join(timing_parts)}"
    
    print(summary_msg)
    sys.stdout.flush()  # Force immediate output to prevent timing issues

    # Get actual ant count (default is 10)
    actual_ants = args.ants if args.ants is not None else 10
    
    # Get actual subcolonies count (default is 4)
    actual_subcolonies = args.subcolonies if args.subcolonies is not None else 4

    return {
        "alg": args.alg,
        "puzzle_size": size_label,
        "f%": fixed_percentage if fixed_percentage is not None else "",
        "ants": actual_ants,
        "subcolonies": actual_subcolonies,
        "q0": args.q0,
        "rho": args.rho,
        "bve": args.evap,
        "timeout": args.timeout,
        "success_rate": round(success_rate, 2),
        "time_mean": average_time,
        "time_std": time_std,
        "iter_mean": average_iter if (args.alg == 0 or args.alg == 2 or args.alg == 3 or args.alg == 4) else "",
        "with_comm": with_comm if (args.alg == 2 or args.alg == 4) else "",
        "without_comm": without_comm if (args.alg == 2 or args.alg == 4) else "",
        "cp_initial_mean": avg_cp_initial if cp_initial_list else "",
        "cp_ant_mean": avg_cp_ant if cp_ant_list else "",
        "cp_total_mean": avg_cp_total if (cp_initial_list and cp_ant_list) else "",
        "acs_time_mean": avg_acs_time if acs_time_list else "",
        "dcm_aco_time_mean": avg_dcm_aco_time if dcm_aco_time_list else "",
        "coop_game_mean": avg_coop_game if coop_game_list else "",
        "pheromone_fusion_mean": avg_pheromone_fusion if pheromone_fusion_list else "",
        "public_path_mean": avg_public_path if public_path_list else "",
        "communication_time_mean": avg_communication_time if communication_time_list else "",
        # Percentages
        "cp_percentage": cp_percentage if (cp_initial_list and cp_ant_list) else "",
        "acs_time_percentage": acs_time_percentage if acs_time_list else "",
        "dcm_aco_time_percentage": dcm_aco_time_percentage if dcm_aco_time_list else "",
        "coop_game_percentage": coop_game_percentage if coop_game_list else "",
        "pheromone_fusion_percentage": pheromone_fusion_percentage if pheromone_fusion_list else "",
        "public_path_percentage": public_path_percentage if public_path_list else "",
        "communication_time_percentage": communication_time_percentage if communication_time_list else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all general Sudoku instances through the solver.")
    parser.add_argument("--instances-root", default=None, help="Folder containing instances (default: runs both instances/general AND instances/logic-solvable)")
    parser.add_argument("--solver", default=None, help="Path to the solver executable (default: auto-detect)")
    parser.add_argument("--output", default=None, help="Destination CSV file for metrics (default: auto-generated based on puzzle size and timestamp).")
    parser.add_argument("--alg", type=int, nargs="+", default=[0], help="Solver algorithm(s) (0=ACS, 1=backtracking, 2=parallel, 3=multi-colony, 4=multi-thread multi-colony). Can specify multiple: --alg 0 2 4")
    parser.add_argument("--timeout", type=float, default=120.0, help="Timeout per puzzle in seconds (default: 120).")
    parser.add_argument("--ants", type=int, default=None, help="Override number of ants for all algorithms (default: 10). Can be overridden by --ants-single or --ants-multi.")
    parser.add_argument("--ants-single", type=int, default=None, help="Number of ants for single-colony algorithms (alg 0 and 2). Overrides --ants for these algorithms.")
    parser.add_argument("--ants-multi", type=int, default=None, help="Number of ants for multi-colony algorithms (alg 3 and 4). Overrides --ants for these algorithms.")
    parser.add_argument("--subcolonies", type=int, default=None, help="Number of sub-colonies for parallel ACS (alg=2, default: 4).")
    parser.add_argument("--threads", type=int, default=None, help="Number of threads for parallel algorithms (alg=2 or alg=4, default: 4).")
    parser.add_argument("--numcolonies", type=int, default=None, help="Number of colonies for multi-colony algorithms (alg=3 or alg=4, default: numacs+1).")
    parser.add_argument("--numacs", type=int, default=None, help="Number of ACS colonies for multi-colony algorithms (alg=3 or alg=4, default: 3).")
    parser.add_argument("--q0", type=float, default=0.9, help="Override ACS q0 parameter.")
    parser.add_argument("--rho", type=float, default=0.9, help="Override ACS rho parameter.")
    parser.add_argument("--evap", type=float, default=0.005, help="Override ACS evaporation parameter.")
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on number of instances to process.")
    parser.add_argument("--single-instance", action="store_true", help="Run only the first matching instance (useful for testing).")
    parser.add_argument("--instance", type=str, default=None, help="Run a specific instance file (e.g., instances/9x9/puzzle1.txt). Overrides --instances-root and --single-instance.")
    parser.add_argument("--puzzle-size", dest="puzzle_sizes", nargs="+", choices=["9x9", "16x16", "25x25", "36x36"], help="Filter by puzzle size(s), e.g. --puzzle-size 25x25.")
    parser.add_argument("--fixed-percentage", dest="fixed_percentages", type=int, nargs="+", help="Filter by fixed-cell percentage(s), e.g. --fixed-percentage 40.")
    parser.add_argument("--solver-timeout", type=float, default=None, help="Wall-clock timeout applied to each solver invocation.")
    parser.add_argument("--solver-verbose", action="store_true", help="Pass --verbose to the solver binary.")
    parser.add_argument("--verbose", action="store_true", default=True, help="Print per-instance progress to the console (default: True).")
    parser.add_argument("--no-verbose", dest="verbose", action="store_false", help="Disable per-instance progress output.")

    args = parser.parse_args()

    repo_root = find_repo_root()

    try:
        solver_path = resolve_solver_path(args.solver)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    # Determine which instances to run
    if args.instance is not None:
        # User specified a specific instance file
        instance_path = (repo_root / args.instance).resolve()
        if not instance_path.exists():
            print(f"Instance file not found: {instance_path}", file=sys.stderr)
            return 1
        metadata_list = [parse_metadata(instance_path)]
        instances_root_display = instance_path.parent
        print(f"Running specific instance: {args.instance}")
    elif args.instances_root is not None:
        # User specified a specific folder
        instances_root = (repo_root / args.instances_root).resolve()
        try:
            instance_files = list(iter_instance_files(instances_root))
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
        if not instance_files:
            print(f"No instances found in '{instances_root}'.", file=sys.stderr)
            return 1
        instances_root_display = instances_root
        
        metadata_list = sort_instance_metadata([parse_metadata(path) for path in instance_files])

        if args.puzzle_sizes:
            allowed_sizes = set(args.puzzle_sizes)
            metadata_list = [meta for meta in metadata_list if meta.size_label in allowed_sizes]

        if args.fixed_percentages:
            allowed_fixed = set(args.fixed_percentages)
            metadata_list = [
                meta
                for meta in metadata_list
                if meta.fixed_percentage is not None and meta.fixed_percentage in allowed_fixed
            ]

        if not metadata_list:
            print("No instances match the specified filters.", file=sys.stderr)
            return 1

        if args.single_instance:
            metadata_list = metadata_list[:1]
            print(f"Running single instance mode: {metadata_list[0].relative_path}")
        elif args.limit is not None:
            metadata_list = metadata_list[: args.limit]
    else:
        # Default: run both general and logic-solvable instances
        try:
            instance_files = list(iter_all_instance_files(repo_root))
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
        instances_root_display = repo_root / "instances" / "(general + logic-solvable)"
        
        metadata_list = sort_instance_metadata([parse_metadata(path) for path in instance_files])

        if args.puzzle_sizes:
            allowed_sizes = set(args.puzzle_sizes)
            metadata_list = [meta for meta in metadata_list if meta.size_label in allowed_sizes]

        if args.fixed_percentages:
            allowed_fixed = set(args.fixed_percentages)
            metadata_list = [
                meta
                for meta in metadata_list
                if meta.fixed_percentage is not None and meta.fixed_percentage in allowed_fixed
            ]

        if not metadata_list:
            print("No instances match the specified filters.", file=sys.stderr)
            return 1

        if args.single_instance:
            metadata_list = metadata_list[:1]
            print(f"Running single instance mode: {metadata_list[0].relative_path}")
        elif args.limit is not None:
            metadata_list = metadata_list[: args.limit]

    # Ensure args.alg is a list
    algorithms = args.alg if isinstance(args.alg, list) else [args.alg]
    
    # Data structure: results_matrix[puzzle_key][algorithm] = stats_dict
    results_matrix: Dict[str, Dict[int, dict]] = {}
    total_instances = len(metadata_list)
    
    # Overall statistics per algorithm
    overall_stats_per_alg: Dict[int, dict] = {}
    for alg in algorithms:
        overall_stats_per_alg[alg] = {
            "total": 0, "successes": 0, "times": [], "iterations": [],
            "with_comm": 0, "without_comm": 0
        }

    # Run each algorithm for each instance
    for algorithm in algorithms:
        print(f"\n{'='*60}")
        print(f"Running Algorithm {algorithm}")
        print(f"{'='*60}\n")

    for idx, metadata in enumerate(metadata_list, start=1):
        # Determine if this is a logic-solvable instance (no fixed_percentage)
        is_logic_solvable = metadata.fixed_percentage is None
        num_runs = 100 if is_logic_solvable else 1
        
        for algorithm in algorithms:
            # Puzzle key for results matrix
            puzzle_key = metadata.size_label
            if puzzle_key not in results_matrix:
                results_matrix[puzzle_key] = {}
            
            # Initialize stats for this algorithm if not exists
            if algorithm not in results_matrix[puzzle_key]:
                results_matrix[puzzle_key][algorithm] = {
                    "total": 0, "successes": 0, "fails": 0, "times": [], "iterations": [],
                    "with_comm": 0, "without_comm": 0,
                    "cp_initial": [], "cp_ant": [], "cp_calls": [],
                    "acs_time": [], "dcm_aco_time": [], "coop_game": [], "pheromone_fusion": [],
                    "public_path": [], "communication_time": []
                }
            
            stats = results_matrix[puzzle_key][algorithm]
            
            # Run the puzzle num_runs times (100 for logic-solvable, 1 for general)
            for run_num in range(1, num_runs + 1):
                cmd = build_solver_command(solver_path, metadata.path, repo_root, args, algorithm)
                # Show progress for algorithm 2 when verbose is enabled
                show_progress = args.verbose and algorithm == 2
                result = run_solver(cmd, repo_root, timeout=args.solver_timeout, show_progress=show_progress)

                success, solve_time, iterations, communication, cp_initial, cp_ant, cp_calls, acs_time, dcm_aco_time, coop_game_time, pheromone_fusion_time, public_path_time, communication_time, stdout_text, stderr_text = parse_solver_output(result.stdout, result.stderr if result.stderr else "")

                if success is False and (solve_time is None or solve_time == 0.0):
                    solve_time = round(float(args.timeout), 5)

                if args.verbose:
                    status = "OK" if success else "FAIL" if success is not None else "UNKNOWN"
                    
                    # Build detailed timing string
                    timing_str = ""
                    if solve_time is not None:
                        timing_str = f"{solve_time:.5f}s"
                        
                        # Add detailed timing breakdown if available
                        timing_parts = []
                        if cp_initial is not None:
                            cp_init_pct = (cp_initial / solve_time * 100) if solve_time > 0 else 0
                            timing_parts.append(f"CP_init={cp_initial:.6f}s ({cp_init_pct:.2f}%)")
                        if cp_ant is not None:
                            cp_ant_pct = (cp_ant / solve_time * 100) if solve_time > 0 else 0
                            timing_parts.append(f"CP_ant={cp_ant:.6f}s ({cp_ant_pct:.2f}%)")
                        if acs_time is not None:
                            acs_pct = (acs_time / solve_time * 100) if solve_time > 0 else 0
                            timing_parts.append(f"ACS={acs_time:.6f}s ({acs_pct:.2f}%)")
                        if dcm_aco_time is not None:
                            dcm_pct = (dcm_aco_time / solve_time * 100) if solve_time > 0 else 0
                            timing_parts.append(f"DCM-ACO={dcm_aco_time:.6f}s ({dcm_pct:.2f}%)")
                        if coop_game_time is not None:
                            coop_pct = (coop_game_time / solve_time * 100) if solve_time > 0 else 0
                            timing_parts.append(f"CoopGame={coop_game_time:.6f}s ({coop_pct:.2f}%)")
                        if pheromone_fusion_time is not None:
                            fusion_pct = (pheromone_fusion_time / solve_time * 100) if solve_time > 0 else 0
                            timing_parts.append(f"PherFusion={pheromone_fusion_time:.6f}s ({fusion_pct:.2f}%)")
                        if public_path_time is not None:
                            public_pct = (public_path_time / solve_time * 100) if solve_time > 0 else 0
                            timing_parts.append(f"PublicPath={public_path_time:.6f}s ({public_pct:.2f}%)")
                        if communication_time is not None:
                            comm_pct = (communication_time / solve_time * 100) if solve_time > 0 else 0
                            timing_parts.append(f"CommTime={communication_time:.6f}s ({comm_pct:.2f}%)")
                        
                        if timing_parts:
                            timing_str = ", ".join(timing_parts) + f", Total={solve_time:.5f}s"
                            if iterations is not None:
                                timing_str += f", {iterations} iter"
                    elif iterations is not None:
                        timing_str += f", {iterations} iter"
                
                    if is_logic_solvable:
                        # For logic-solvable, show run number
                        if timing_str:
                            print(f"[alg {algorithm}] [run {run_num}/{num_runs}] {metadata.relative_path} -> {status} ({timing_str})")
                        else:
                            print(f"[alg {algorithm}] [run {run_num}/{num_runs}] {metadata.relative_path} -> {status}")
                    else:
                        # For general instances, show normal format
                        if timing_str:
                            print(f"[alg {algorithm}] [{idx}/{total_instances}] {metadata.relative_path} -> {status} ({timing_str})")
                        else:
                            print(f"[alg {algorithm}] [{idx}/{total_instances}] {metadata.relative_path} -> {status}")

                stats["total"] += 1
                if success:
                    stats["successes"] += 1
                else:
                    stats["fails"] += 1
                
                # Only include times and iterations from successful runs in statistics
                if success and solve_time is not None:
                    stats["times"].append(solve_time)
                    # Track iterations for all algorithms that support it (0, 2, 3, 4)
                    if iterations is not None and (algorithm == 0 or algorithm == 2 or algorithm == 3 or algorithm == 4):
                        stats["iterations"].append(iterations)
                    # Track communication for algorithms 2 and 4
                    if communication is not None and (algorithm == 2 or algorithm == 4):
                        if communication:
                            stats["with_comm"] += 1
                        else:
                            stats["without_comm"] += 1
                    # Track CP timing statistics
                    if cp_initial is not None:
                        stats["cp_initial"].append(cp_initial)
                    if cp_ant is not None:
                        stats["cp_ant"].append(cp_ant)
                    if cp_calls is not None:
                        stats["cp_calls"].append(cp_calls)
                    # Track new timing statistics
                    if acs_time is not None:
                        stats["acs_time"].append(acs_time)
                    if dcm_aco_time is not None:
                        stats["dcm_aco_time"].append(dcm_aco_time)
                    if coop_game_time is not None:
                        stats["coop_game"].append(coop_game_time)
                    if pheromone_fusion_time is not None:
                        stats["pheromone_fusion"].append(pheromone_fusion_time)
                    if public_path_time is not None:
                        stats["public_path"].append(public_path_time)
                    if communication_time is not None:
                        stats["communication_time"].append(communication_time)

                # Update overall stats
                overall_stats_per_alg[algorithm]["total"] += 1
                if success:
                    overall_stats_per_alg[algorithm]["successes"] += 1
                if success and solve_time is not None:
                    overall_stats_per_alg[algorithm]["times"].append(solve_time)
                    if iterations is not None and (algorithm == 0 or algorithm == 2 or algorithm == 3 or algorithm == 4):
                        overall_stats_per_alg[algorithm]["iterations"].append(iterations)
                    if communication is not None and (algorithm == 2 or algorithm == 4):
                        if communication:
                            overall_stats_per_alg[algorithm]["with_comm"] += 1
                        else:
                            overall_stats_per_alg[algorithm]["without_comm"] += 1

    # Generate output filename
    if args.output is not None:
        output_path = (repo_root / args.output).resolve()
    else:
        # Auto-generate filename based on puzzle sizes and timestamp
        puzzle_sizes = sorted(set(m.size_label for m in metadata_list))
        size_str = "_".join(puzzle_sizes)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Run_{size_str}_{timestamp}.csv"
        output_path = (repo_root / "results" / filename).resolve()
    
    # Convert results_matrix to CSV rows (wide format)
    csv_rows = []
    for puzzle_size in sorted(results_matrix.keys()):
        row = {"puzzle_size": puzzle_size}
        for alg in sorted(algorithms):
            if alg in results_matrix[puzzle_size]:
                stats = results_matrix[puzzle_size][alg]
                
                # Get actual parameter values based on algorithm
                # Ant count depends on algorithm type
                if alg in [0, 2]:
                    # Single-colony algorithms: use --ants-single, fallback to --ants, default to 10
                    actual_ants = args.ants_single if args.ants_single is not None else (args.ants if args.ants is not None else 10)
                elif alg in [3, 4]:
                    # Multi-colony algorithms: use --ants-multi, fallback to --ants, default to 10
                    actual_ants = args.ants_multi if args.ants_multi is not None else (args.ants if args.ants is not None else 10)
                else:
                    actual_ants = args.ants if args.ants is not None else 10
                
                actual_threads = args.threads if args.threads is not None else 4
                actual_numcolonies = args.numcolonies if args.numcolonies is not None else (args.numacs + 1 if args.numacs is not None else 4)
                actual_numacs = args.numacs if args.numacs is not None else 3
                
                # Calculate statistics
                success_rate = (stats["successes"] / stats["total"] * 100) if stats["total"] > 0 else 0
                time_mean = statistics.mean(stats["times"]) if stats["times"] else 0
                time_std = statistics.stdev(stats["times"]) if len(stats["times"]) > 1 else 0
                iter_mean = statistics.mean(stats["iterations"]) if stats["iterations"] else 0
                
                # Calculate mean times (for display)
                cp_initial_mean = statistics.mean(stats["cp_initial"]) if stats["cp_initial"] else 0
                cp_ant_mean = statistics.mean(stats["cp_ant"]) if stats["cp_ant"] else 0
                acs_time_mean = statistics.mean(stats["acs_time"]) if stats["acs_time"] else 0
                dcm_aco_time_mean = statistics.mean(stats["dcm_aco_time"]) if stats["dcm_aco_time"] else 0
                coop_game_mean = statistics.mean(stats["coop_game"]) if stats["coop_game"] else 0
                pheromone_fusion_mean = statistics.mean(stats["pheromone_fusion"]) if stats["pheromone_fusion"] else 0
                public_path_mean = statistics.mean(stats["public_path"]) if stats["public_path"] else 0
                communication_time_mean = statistics.mean(stats["communication_time"]) if stats["communication_time"] else 0
                cp_total_mean = cp_initial_mean + cp_ant_mean
                
                # Calculate percentages correctly: sum all times, then compute percentage
                # This gives the overall proportion of time spent on each component
                cp_initial_sum = sum(stats["cp_initial"]) if stats["cp_initial"] else 0
                cp_ant_sum = sum(stats["cp_ant"]) if stats["cp_ant"] else 0
                acs_time_sum = sum(stats["acs_time"]) if stats["acs_time"] else 0
                dcm_aco_time_sum = sum(stats["dcm_aco_time"]) if stats["dcm_aco_time"] else 0
                coop_game_sum = sum(stats["coop_game"]) if stats["coop_game"] else 0
                pheromone_fusion_sum = sum(stats["pheromone_fusion"]) if stats["pheromone_fusion"] else 0
                public_path_sum = sum(stats["public_path"]) if stats["public_path"] else 0
                communication_time_sum = sum(stats["communication_time"]) if stats["communication_time"] else 0
                time_sum = sum(stats["times"]) if stats["times"] else 0
                
                # Calculate percentages from sums
                cp_initial_percentage = (cp_initial_sum / time_sum * 100) if time_sum > 0 else 0
                cp_ant_percentage = (cp_ant_sum / time_sum * 100) if time_sum > 0 else 0
                acs_time_percentage = (acs_time_sum / time_sum * 100) if time_sum > 0 else 0
                dcm_aco_time_percentage = (dcm_aco_time_sum / time_sum * 100) if time_sum > 0 else 0
                coop_game_percentage = (coop_game_sum / time_sum * 100) if time_sum > 0 else 0
                pheromone_fusion_percentage = (pheromone_fusion_sum / time_sum * 100) if time_sum > 0 else 0
                public_path_percentage = (public_path_sum / time_sum * 100) if time_sum > 0 else 0
                communication_time_percentage = (communication_time_sum / time_sum * 100) if time_sum > 0 else 0
                cp_percentage = ((cp_initial_sum + cp_ant_sum) / time_sum * 100) if time_sum > 0 else 0
                
                # Add algorithm-specific columns with N/A handling
                row[f"nAnts_alg{alg}"] = get_value_for_alg(alg, "nAnts", actual_ants)
                row[f"threads_alg{alg}"] = get_value_for_alg(alg, "threads", actual_threads)
                row[f"numcolonies_alg{alg}"] = get_value_for_alg(alg, "numcolonies", actual_numcolonies)
                row[f"numacs_alg{alg}"] = get_value_for_alg(alg, "numacs", actual_numacs)
                row[f"q0_alg{alg}"] = args.q0
                row[f"rho_alg{alg}"] = args.rho
                row[f"bve_alg{alg}"] = args.evap
                row[f"timeout_alg{alg}"] = args.timeout
                row[f"success_rate_alg{alg}"] = f"{success_rate:.2f}"
                row[f"time_mean_alg{alg}"] = f"{time_mean:.6f}"
                row[f"time_std_alg{alg}"] = f"{time_std:.6f}"
                row[f"iter_mean_alg{alg}"] = f"{iter_mean:.2f}" if iter_mean > 0 else "N/A"
                row[f"with_comm_alg{alg}"] = get_value_for_alg(alg, "with_comm", stats["with_comm"])
                row[f"without_comm_alg{alg}"] = get_value_for_alg(alg, "without_comm", stats["without_comm"])
                
                # Time means (all together)
                row[f"cp_initial_mean_alg{alg}"] = f"{cp_initial_mean:.6f}"
                row[f"cp_ant_mean_alg{alg}"] = f"{cp_ant_mean:.6f}"
                row[f"cp_total_mean_alg{alg}"] = f"{cp_total_mean:.6f}"
                # Main algorithm time (ACS or DCM-ACO)
                if alg in [0, 2]:
                    row[f"acs_time_mean_alg{alg}"] = f"{acs_time_mean:.6f}"
                    row[f"dcm_aco_time_mean_alg{alg}"] = "N/A"
                elif alg in [3, 4]:
                    row[f"acs_time_mean_alg{alg}"] = "N/A"
                    row[f"dcm_aco_time_mean_alg{alg}"] = f"{dcm_aco_time_mean:.6f}"
                else:
                    row[f"acs_time_mean_alg{alg}"] = "N/A"
                    row[f"dcm_aco_time_mean_alg{alg}"] = "N/A"
                # Sub-components (for DCM-ACO)
                row[f"coop_game_mean_alg{alg}"] = get_value_for_alg(alg, "coop_game_mean", f"{coop_game_mean:.6f}")
                row[f"pheromone_fusion_mean_alg{alg}"] = get_value_for_alg(alg, "pheromone_fusion_mean", f"{pheromone_fusion_mean:.6f}")
                row[f"public_path_mean_alg{alg}"] = get_value_for_alg(alg, "public_path_mean", f"{public_path_mean:.6f}")
                row[f"communication_time_mean_alg{alg}"] = get_value_for_alg(alg, "communication_time_mean", f"{communication_time_mean:.6f}")
                
                # All percentages grouped together at the end
                row[f"cp_percentage_alg{alg}"] = f"{cp_percentage:.2f}"
                # Main algorithm percentage (ACS or DCM-ACO)
                if alg in [0, 2]:
                    row[f"acs_time_percentage_alg{alg}"] = f"{acs_time_percentage:.2f}"
                    row[f"dcm_aco_time_percentage_alg{alg}"] = "N/A"
                elif alg in [3, 4]:
                    row[f"acs_time_percentage_alg{alg}"] = "N/A"
                    row[f"dcm_aco_time_percentage_alg{alg}"] = f"{dcm_aco_time_percentage:.2f}"
                else:
                    row[f"acs_time_percentage_alg{alg}"] = "N/A"
                    row[f"dcm_aco_time_percentage_alg{alg}"] = "N/A"
                # Sub-component percentages
                row[f"coop_game_percentage_alg{alg}"] = get_value_for_alg(alg, "coop_game_percentage", f"{coop_game_percentage:.2f}")
                row[f"pheromone_fusion_percentage_alg{alg}"] = get_value_for_alg(alg, "pheromone_fusion_percentage", f"{pheromone_fusion_percentage:.2f}")
                row[f"public_path_percentage_alg{alg}"] = get_value_for_alg(alg, "public_path_percentage", f"{public_path_percentage:.2f}")
                row[f"communication_time_percentage_alg{alg}"] = get_value_for_alg(alg, "communication_time_percentage", f"{communication_time_percentage:.2f}")
        
        csv_rows.append(row)
    
    write_csv(output_path, csv_rows, algorithms)

    # Print summary per algorithm
    print("\n" + "="*60)
    print("===== Summary =====")
    print(f"Solver binary   : {solver_path}")
    print(f"Instances folder: {instances_root_display}")
    print(f"Output CSV      : {output_path}")
    
    for alg in algorithms:
        print(f"\n--- Algorithm {alg} ---")
        overall = overall_stats_per_alg[alg]
        total = overall["total"]
        successes = overall["successes"]
        failures = total - successes
        avg_time = statistics.mean(overall["times"]) if overall["times"] else 0
        avg_iterations = statistics.mean(overall["iterations"]) if overall["iterations"] else None
        
        # Get actual parameter values based on algorithm
        # Ant count depends on algorithm type
        if alg in [0, 2]:
            # Single-colony algorithms: use --ants-single, fallback to --ants, default to 10
            actual_ants = args.ants_single if args.ants_single is not None else (args.ants if args.ants is not None else 10)
        elif alg in [3, 4]:
            # Multi-colony algorithms: use --ants-multi, fallback to --ants, default to 10
            actual_ants = args.ants_multi if args.ants_multi is not None else (args.ants if args.ants is not None else 10)
        else:
            actual_ants = args.ants if args.ants is not None else 10
        
        actual_threads = args.threads if args.threads is not None else 4
        actual_numcolonies = args.numcolonies if args.numcolonies is not None else (args.numacs + 1 if args.numacs is not None else 4)
        actual_numacs = args.numacs if args.numacs is not None else 3
        
        print(f"Ants            : {actual_ants}")
        if alg == 2 or alg == 4:
            print(f"Threads         : {actual_threads}")
        if alg == 3 or alg == 4:
            print(f"Num Colonies    : {actual_numcolonies}")
            print(f"Num ACS         : {actual_numacs}")
        print(f"q0              : {args.q0}")
        print(f"rho             : {args.rho}")
        print(f"bve             : {args.evap}")
        print(f"Timeout         : {args.timeout}s")
        print(f"Total puzzles   : {total}")
        print(f"Succeeded       : {successes}")
        print(f"Failed          : {failures}")
        if total:
            print(f"Average time    : {avg_time:.5f} s")
            if avg_iterations is not None:
                print(f"Average iters   : {avg_iterations:.2f}")
                if (alg == 2 or alg == 4) and (overall["with_comm"] > 0 or overall["without_comm"] > 0):
                    total_comm = overall["with_comm"] + overall["without_comm"]
                    print(f"With comm       : {overall['with_comm']}/{total_comm} ({(overall['with_comm'] / total_comm * 100.0):.1f}%)")
        else:
            print(f"Average time    : n/a")
    
    print("="*60)
    sys.stdout.flush()  # Force immediate output to prevent timing issues

    # Display time breakdown for single instance runs
    if args.instance is not None or (args.single_instance and len(metadata_list) == 1):
        for alg in algorithms:
            print(f"\n==Time Breakdown== (Algorithm {alg})")
            
            # Get the stats for this algorithm
            puzzle_key = metadata_list[0].size_label
            if puzzle_key in results_matrix and alg in results_matrix[puzzle_key]:
                stats = results_matrix[puzzle_key][alg]
                
                if stats["times"]:
                    total_time = stats["times"][0] if len(stats["times"]) == 1 else sum(stats["times"]) / len(stats["times"])
                    
                    # Get timing values
                    cp_init = stats["cp_initial"][0] if stats["cp_initial"] and len(stats["cp_initial"]) == 1 else (sum(stats["cp_initial"]) / len(stats["cp_initial"]) if stats["cp_initial"] else 0)
                    cp_ant = stats["cp_ant"][0] if stats["cp_ant"] and len(stats["cp_ant"]) == 1 else (sum(stats["cp_ant"]) / len(stats["cp_ant"]) if stats["cp_ant"] else 0)
                    
                    # Calculate percentages
                    cp_init_pct = (cp_init / total_time * 100) if total_time > 0 else 0
                    cp_ant_pct = (cp_ant / total_time * 100) if total_time > 0 else 0
                    
                    # Display Initial CP and Ant CP
                    print(f"Initial CP Time: {cp_init:.6f} s ({cp_init_pct:.2f}%)")
                    print(f"Ant CP Time: {cp_ant:.6f} s ({cp_ant_pct:.2f}%)")
                    
                    # Show ACS time for algorithms 0, 2
                    if alg in [0, 2] and stats["acs_time"]:
                        acs = stats["acs_time"][0] if len(stats["acs_time"]) == 1 else sum(stats["acs_time"]) / len(stats["acs_time"])
                        acs_pct = (acs / total_time * 100) if total_time > 0 else 0
                        print(f"ACS Time: {acs:.6f} s ({acs_pct:.2f}%)")
                    
                    # Show DCM-ACO time and sub-components for algorithms 3, 4
                    if alg in [3, 4] and stats["dcm_aco_time"]:
                        dcm = stats["dcm_aco_time"][0] if len(stats["dcm_aco_time"]) == 1 else sum(stats["dcm_aco_time"]) / len(stats["dcm_aco_time"])
                        dcm_pct = (dcm / total_time * 100) if total_time > 0 else 0
                        print(f"DCM-ACO Time: {dcm:.6f} s ({dcm_pct:.2f}%)")
                        
                        # Sub-components with "  - " prefix
                        if stats["coop_game"]:
                            coop = stats["coop_game"][0] if len(stats["coop_game"]) == 1 else sum(stats["coop_game"]) / len(stats["coop_game"])
                            coop_pct = (coop / total_time * 100) if total_time > 0 else 0
                            print(f"  - Cooperative Game Time: {coop:.6f} s ({coop_pct:.2f}%)")
                        
                        if stats["pheromone_fusion"]:
                            fusion = stats["pheromone_fusion"][0] if len(stats["pheromone_fusion"]) == 1 else sum(stats["pheromone_fusion"]) / len(stats["pheromone_fusion"])
                            fusion_pct = (fusion / total_time * 100) if total_time > 0 else 0
                            print(f"  - Pheromone Fusion Time: {fusion:.6f} s ({fusion_pct:.2f}%)")
                        
                        if stats["public_path"]:
                            public = stats["public_path"][0] if len(stats["public_path"]) == 1 else sum(stats["public_path"]) / len(stats["public_path"])
                            public_pct = (public / total_time * 100) if total_time > 0 else 0
                            print(f"  - Public Path Recommendation Time: {public:.6f} s ({public_pct:.2f}%)")
                    
                    # Show communication time for algorithms 2, 4
                    if alg in [2, 4] and stats["communication_time"]:
                        comm = stats["communication_time"][0] if len(stats["communication_time"]) == 1 else sum(stats["communication_time"]) / len(stats["communication_time"])
                        comm_pct = (comm / total_time * 100) if total_time > 0 else 0
                        print(f"Communication Time: {comm:.6f} s ({comm_pct:.2f}%)")
                    
                    # Total Solve Time at the end
                    print(f"Total Solve Time: {total_time:.6f} s")
                else:
                    print("No successful runs")

    return 0


if __name__ == "__main__":
    sys.exit(main())

