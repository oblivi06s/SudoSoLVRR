# AblationScript.py - Usage Guide

## Overview
`AblationScript.py` runs ablation studies on the Sudoku solver, testing different parameter values while keeping other parameters constant. Results are output to an Excel file with a structured format.

## Installation

Install required dependencies:
```bash
pip install openpyxl
```

## Basic Usage

### Test Different Ant Counts
```bash
python scripts/AblationScript.py \
    --parameter ants \
    --values 4 5 10 15 20 \
    --alg 4 \
    --output results/ablation_ants.xlsx \
    --q0 0.9 \
    --rho 0.9 \
    --evap 0.005 \
    --threads 3 \
    --numacs 3 \
    --numcolonies 4 \
    --timeout 120
```

### Test Different q0 Values
```bash
python scripts/AblationScript.py \
    --parameter q0 \
    --values 0.0 0.3 0.5 0.7 0.9 0.95 1.0 \
    --alg 4 \
    --output results/ablation_q0.xlsx \
    --ants 10 \
    --rho 0.9 \
    --evap 0.005 \
    --threads 3 \
    --numacs 3 \
    --numcolonies 4 \
    --timeout 120
```

### Test Different Thread Counts
```bash
python scripts/AblationScript.py \
    --parameter threads \
    --values 1 2 3 4 6 8 \
    --alg 4 \
    --output results/ablation_threads.xlsx \
    --ants 10 \
    --q0 0.9 \
    --rho 0.9 \
    --evap 0.005 \
    --numacs 3 \
    --numcolonies 4 \
    --timeout 120
```

## Command-Line Arguments

### Required Arguments
- `--parameter`: Parameter to vary (e.g., "ants", "q0", "rho", "threads")
- `--values`: List of values to test (space-separated)
- `--output`: Output Excel file path

### Algorithm Selection
- `--alg`: Algorithm to use (0-4, default: 4)
  - 0: Single-threaded ACS
  - 2: Parallel ACS
  - 3: Multi-Colony (single-threaded)
  - 4: Multi-Thread Multi-Colony (default)

### Instance Selection
- `--instances-root`: Folder containing instances (default: `instances/general`)

### Constant Parameters
Specify these to keep them constant during the ablation study:
- `--ants`: Number of ants
- `--q0`: q0 parameter (exploitation vs exploration)
- `--rho`: rho parameter (pheromone persistence)
- `--evap`: Evaporation rate
- `--threads`: Number of threads (for algorithms 2, 4)
- `--numacs`: Number of ACS colonies (for algorithms 3, 4)
- `--numcolonies`: Total number of colonies (for algorithms 3, 4)
- `--subcolonies`: Number of sub-colonies (legacy)
- `--convthreshold`: Convergence threshold (for algorithms 3, 4)
- `--entropythreshold`: Entropy threshold (for algorithms 3, 4)
- `--comm-early-interval`: Early communication interval (for algorithms 2, 4)
- `--comm-late-interval`: Late communication interval (for algorithms 2, 4)
- `--comm-threshold`: Communication threshold (for algorithms 2, 4)
- `--timeout`: Timeout per puzzle in seconds (default: 120)

### Other Options
- `--solver`: Path to solver executable (default: auto-detect)
- `--runs-per-instance`: Number of runs per general instance (default: 1; logic-solvable instances always use 100 runs)
- `--verbose`: Print progress (default: True)
- `--no-verbose`: Disable progress output

## Valid Parameters

The following parameters can be varied:
- `ants`: Number of ants (integer)
- `q0`: Exploitation vs exploration (float, 0.0-1.0)
- `rho`: Pheromone persistence (float, 0.0-1.0)
- `evap`: Evaporation rate (float)
- `threads`: Number of threads (integer, for algorithms 2, 4)
- `numacs`: Number of ACS colonies (integer, for algorithms 3, 4)
- `numcolonies`: Total number of colonies (integer, for algorithms 3, 4)
- `subcolonies`: Number of sub-colonies (integer)
- `convthreshold`: Convergence threshold (float, for algorithms 3, 4)
- `entropythreshold`: Entropy threshold (float, for algorithms 3, 4)
- `comm-early-interval`: Early communication interval (integer, for algorithms 2, 4)
- `comm-late-interval`: Late communication interval (integer, for algorithms 2, 4)
- `comm-threshold`: Communication threshold (integer, for algorithms 2, 4)

## Excel Output Format

The Excel file contains:

1. **Constant Parameters Section** (top rows):
   - Lists all constant parameters and their values
   - Shows what stayed the same during the ablation study

2. **Results Section**:
   - Header row: Parameter Value | Instance | Success Rate (%) | Average Time (s) | Std Dev (s) | Avg Iteration
   - For each parameter value:
     - Label row with parameter value (e.g., "ants = 4")
     - Results rows for each instance/puzzle size
     - Empty row separator between parameter groups

## Example Output Structure

```
A1: Constant Parameters
A2: Parameter          | B2: Value
A3: algorithm          | B3: 4
A4: q0                 | B4: 0.9
A5: rho                | B5: 0.9
...

A12: Parameter Value   | B12: Instance | C12: Success Rate (%) | D12: Average Time (s) | E12: Std Dev (s) | F12: Avg Iteration
A13: ants = 4
A14:                   | B14: 9x9      | C14: 95.5            | D14: 2.345            | E14: 0.123        | F14: 150.2
A15:                   | B15: 16x16    | C15: 87.3            | D15: 15.678           | E15: 2.456        | F15: 450.8
A16: (empty row)
A17: ants = 5
...
```

## Notes

1. **Logic-Solvable Instances**: Instances without a fixed percentage (logic-solvable) automatically run 100 times for statistical significance. General instances run once by default (or as specified by `--runs-per-instance`).

2. **Parameter Values**: Integer parameters (ants, threads, etc.) should be specified as integers. Float parameters (q0, rho, etc.) should be specified as floats.

3. **Statistics**: 
   - Success Rate: Percentage of successful runs
   - Average Time: Mean solve time (only from successful runs)
   - Std Dev: Standard deviation of solve times (only from successful runs)
   - Avg Iteration: Mean number of iterations (only from successful runs)

4. **Progress**: The script shows progress for each parameter value and instance being tested. For multiple runs, it shows a status indicator (OK/FAIL) for each run.

## Tips

- Start with a small set of instances to test your configuration
- Use `--no-verbose` for batch processing to reduce output
- Results are aggregated by puzzle size (9x9, 16x16, etc.)
- The script automatically creates the output directory if it doesn't exist
