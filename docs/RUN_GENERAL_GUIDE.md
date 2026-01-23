# run_general.py - User Guide

## Overview

`run_general.py` is a Python script for batch-running Sudoku instances through the solver with various algorithms and configurations. It automatically collects statistics, generates CSV reports, and provides detailed timing breakdowns.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Command-Line Arguments](#command-line-arguments)
- [Algorithm Selection](#algorithm-selection)
- [Running Multiple Algorithms](#running-multiple-algorithms)
- [Instance Selection](#instance-selection)
- [Parameter Configuration](#parameter-configuration)
- [Output Options](#output-options)
- [Common Use Cases](#common-use-cases)
- [CSV Output Format](#csv-output-format)
- [Understanding the Results](#understanding-the-results)

---

## Basic Usage

### Simplest Run
```bash
python scripts/run_general.py
```
- Runs algorithm 0 (ACS) on all instances in `instances/general` and `instances/logic-solvable`
- Auto-generates output CSV with timestamp
- Uses default parameters (10 ants, q0=0.9, rho=0.9)

### Run on Specific Instance Folder
```bash
python scripts/run_general.py --instances-root instances/paquita-database
```

### Run with Specific Algorithm
```bash
python scripts/run_general.py --alg 2
```

---

## Command-Line Arguments

### Instance Selection

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--instances-root` | path | `None` | Folder containing instances. If not specified, runs both `instances/general` and `instances/logic-solvable` |
| `--puzzle-size` | list | `None` | Filter by puzzle size(s). Choices: `9x9`, `16x16`, `25x25`, `36x36` |
| `--fixed-percentage` | list | `None` | Filter by fixed-cell percentage(s) |
| `--limit` | int | `None` | Cap on number of instances to process |
| `--single-instance` | flag | `False` | Run only the first matching instance (useful for testing) |

### Algorithm Selection

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--alg` | list | `[0]` | Algorithm(s) to run. Can specify multiple. See [Algorithm Selection](#algorithm-selection) |

### Solver Parameters

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--ants` | int | `10` | Number of ants for all algorithms (can be overridden by `--ants-single` or `--ants-multi`) |
| `--ants-single` | int | `None` | Number of ants for single-colony algorithms (alg 0 and 2). Overrides `--ants` |
| `--ants-multi` | int | `None` | Number of ants for multi-colony algorithms (alg 3 and 4). Overrides `--ants` |
| `--threads` | int | `4` | Number of threads (for algorithms 2 and 4) |
| `--numcolonies` | int | `numacs+1` | Number of colonies (for algorithms 3 and 4) |
| `--numacs` | int | `3` | Number of ACS colonies (for algorithms 3 and 4) |
| `--subcolonies` | int | `4` | Number of sub-colonies (legacy, use `--threads` instead) |
| `--q0` | float | `0.9` | ACS q0 parameter (exploitation vs exploration) |
| `--rho` | float | `0.9` | ACS rho parameter (pheromone persistence) |
| `--evap` | float | `0.005` | ACS evaporation parameter |
| `--timeout` | float | `120.0` | Timeout per puzzle in seconds |

### Output Options

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--output` | path | auto-generated | Destination CSV file. Default: `Run_{size}_{timestamp}.csv` |
| `--verbose` | flag | `True` | Print per-instance progress (default enabled) |
| `--no-verbose` | flag | - | Disable per-instance progress output |
| `--solver-verbose` | flag | `False` | Pass `--verbose` to the solver binary |

### Advanced Options

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--solver` | path | auto-detect | Path to the solver executable |
| `--solver-timeout` | float | `None` | Wall-clock timeout for each solver invocation |

---

## Algorithm Selection

The `--alg` argument specifies which algorithm(s) to use:

| Algorithm | Name | Description | Applicable Parameters |
|-----------|------|-------------|----------------------|
| `0` | ACS | Standard Ant Colony System | `--ants`, `--q0`, `--rho`, `--evap` |
| `1` | Backtracking | Traditional backtracking solver | None |
| `2` | Parallel ACS | Multi-threaded parallel ACS | `--ants`, `--threads`, `--q0`, `--rho`, `--evap` |
| `3` | Multi-Colony | Single-threaded multi-colony system | `--ants`, `--numcolonies`, `--numacs`, `--q0`, `--rho`, `--evap` |
| `4` | Multi-Thread Multi-Colony | Parallel multi-colony system | `--ants`, `--threads`, `--numcolonies`, `--numacs`, `--q0`, `--rho`, `--evap` |

---

## Running Multiple Algorithms

You can run multiple algorithms in a single execution by specifying multiple values for `--alg`:

```bash
python scripts/run_general.py --alg 0 2 4
```

This will:
1. Run algorithm 0 on all instances
2. Run algorithm 2 on all instances
3. Run algorithm 4 on all instances
4. Generate a single CSV with results for all algorithms in wide format
5. Print separate summaries for each algorithm

**Benefits:**
- Consistent test conditions across algorithms
- Single CSV file for easy comparison
- Automatic timestamp ensures results are grouped together

---

## Instance Selection

### Run All Default Instances
```bash
python scripts/run_general.py
```
Runs on both `instances/general` and `instances/logic-solvable`

### Run Specific Folder
```bash
python scripts/run_general.py --instances-root instances/paquita-database
```

### Filter by Puzzle Size
```bash
# Single size
python scripts/run_general.py --puzzle-size 9x9

# Multiple sizes
python scripts/run_general.py --puzzle-size 9x9 16x16
```

### Filter by Fixed Percentage
```bash
# Single percentage
python scripts/run_general.py --fixed-percentage 40

# Multiple percentages
python scripts/run_general.py --fixed-percentage 30 40 50
```

### Combine Filters
```bash
python scripts/run_general.py --puzzle-size 9x9 --fixed-percentage 40 --instances-root instances/general
```

### Test with Single Instance
```bash
python scripts/run_general.py --single-instance --instances-root instances/paquita-database
```
Useful for quick testing before running full batch

### Limit Number of Instances
```bash
python scripts/run_general.py --limit 10
```
Process only the first 10 instances

---

## Parameter Configuration

### Understanding Ant Count Parameters

The script provides flexible ant count configuration:

**Three ways to specify ant counts:**
1. **`--ants`**: Global default for all algorithms (default: 10)
2. **`--ants-single`**: Specific count for single-colony algorithms (0, 2)
3. **`--ants-multi`**: Specific count for multi-colony algorithms (3, 4)

**Priority order:**
- For algorithms 0 and 2: `--ants-single` → `--ants` → 10
- For algorithms 3 and 4: `--ants-multi` → `--ants` → 10

**Why separate ant counts?**
- Single-colony algorithms (0, 2) often work well with fewer ants
- Multi-colony algorithms (3, 4) benefit from more ants per colony
- This allows fair comparison between algorithm types

**Examples:**
```bash
# All algorithms use 10 ants
python scripts/run_general.py --alg 0 2 3 4 --ants 10

# Algorithms 0,2 use 3 ants; algorithms 3,4 use 10 ants
python scripts/run_general.py --alg 0 2 3 4 --ants-single 3 --ants-multi 10

# Algorithms 0,2 use 5 ants; algorithms 3,4 use default (10)
python scripts/run_general.py --alg 0 2 3 4 --ants-single 5

# Override global default: 0,2 use 3; 3,4 use 15
python scripts/run_general.py --alg 0 2 3 4 --ants 15 --ants-single 3
```

### Basic ACO Parameters
```bash
python scripts/run_general.py --ants 20 --q0 0.95 --rho 0.85
```

### Algorithm-Specific Ant Counts
```bash
# Different ant counts for single-colony (0,2) vs multi-colony (3,4) algorithms
python scripts/run_general.py --alg 0 2 3 4 \
    --ants-single 3 \
    --ants-multi 10 \
    --threads 4

# Use global --ants with override for single-colony algorithms
python scripts/run_general.py --alg 0 3 4 \
    --ants 10 \
    --ants-single 3
```

### Parallel Algorithm Configuration
```bash
# Algorithm 2: Parallel ACS
python scripts/run_general.py --alg 2 --threads 8 --ants-single 10

# Algorithm 4: Multi-Thread Multi-Colony
python scripts/run_general.py --alg 4 --threads 8 --ants-multi 10 --numacs 5 --numcolonies 6
```

### Multi-Colony Configuration
```bash
# Algorithm 3: Single-threaded multi-colony
python scripts/run_general.py --alg 3 --numacs 5 --numcolonies 6

# Algorithm 4: Multi-threaded multi-colony
python scripts/run_general.py --alg 4 --threads 4 --numacs 3 --numcolonies 4
```

### Timeout Configuration
```bash
# Increase timeout for harder puzzles
python scripts/run_general.py --timeout 300.0

# Add wall-clock timeout as safety
python scripts/run_general.py --timeout 300.0 --solver-timeout 310.0
```

---

## Output Options

### Auto-Generated Filename (Default)
```bash
python scripts/run_general.py --instances-root instances/paquita-database
```
Generates: `results/Run_9x9_20260123_143052.csv`

### Custom Output File
```bash
python scripts/run_general.py --output my_results.csv
```
Saves to: `my_results.csv`

### Custom Output Directory
```bash
python scripts/run_general.py --output results/experiment1/test.csv
```

### Disable Verbose Output
```bash
python scripts/run_general.py --no-verbose
```
Only shows final summary, no per-instance progress

---

## Common Use Cases

### 1. Quick Test Run
```bash
python scripts/run_general.py --single-instance --alg 0 --instances-root instances/paquita-database
```

### 2. Compare All Algorithms
```bash
python scripts/run_general.py --alg 0 1 2 3 4 --instances-root instances/paquita-database
```

### 3. Benchmark Parallel Performance
```bash
# Test different thread counts
python scripts/run_general.py --alg 2 --threads 2 --output results/threads_2.csv
python scripts/run_general.py --alg 2 --threads 4 --output results/threads_4.csv
python scripts/run_general.py --alg 2 --threads 8 --output results/threads_8.csv
```

### 4. Parameter Sweep
```bash
# Test different ant counts
for ants in 5 10 15 20; do
    python scripts/run_general.py --alg 0 --ants $ants --output "results/ants_${ants}.csv"
done
```

### 5. Large-Scale Experiment
```bash
python scripts/run_general.py \
    --alg 0 2 4 \
    --instances-root instances/paquita-database \
    --ants-single 5 \
    --ants-multi 20 \
    --threads 8 \
    --timeout 300.0 \
    --output results/large_scale_experiment.csv
```

### 6. Logic-Solvable Puzzles Only
```bash
python scripts/run_general.py --instances-root instances/logic-solvable
```
Note: Logic-solvable instances run 100 times each for statistical significance

### 7. Specific Puzzle Size Comparison
```bash
python scripts/run_general.py \
    --alg 0 2 4 \
    --puzzle-size 16x16 \
    --ants-single 10 \
    --ants-multi 15 \
    --threads 8
```

### 8. Multi-Colony Parameter Testing
```bash
python scripts/run_general.py \
    --alg 3 4 \
    --numacs 3 \
    --numcolonies 4 \
    --instances-root instances/paquita-database
```

---

## CSV Output Format

### Wide Format Structure

The output CSV uses a **wide format** where each row represents a puzzle size, and columns are algorithm-specific:

```csv
puzzle_size,nAnts_alg0,threads_alg0,time_mean_alg0,iter_mean_alg0,nAnts_alg2,threads_alg2,time_mean_alg2,...
9x9,10,N/A,1.234567,150.00,10,4,0.987654,...
16x16,10,N/A,5.678901,320.00,10,4,3.456789,...
```

### Column Naming Convention

All columns (except `puzzle_size`) follow the pattern: `{metric}_alg{X}`

Examples:
- `nAnts_alg0` - Number of ants for algorithm 0
- `time_mean_alg2` - Mean solve time for algorithm 2
- `threads_alg4` - Number of threads for algorithm 4
- `coop_game_mean_alg3` - Mean cooperative game time for algorithm 3

### Available Metrics per Algorithm

| Metric | Alg 0 | Alg 1 | Alg 2 | Alg 3 | Alg 4 | Description |
|--------|-------|-------|-------|-------|-------|-------------|
| `nAnts` | ✓ | ✗ | ✓ | ✓ | ✓ | Number of ants |
| `threads` | N/A | N/A | ✓ | N/A | ✓ | Number of threads |
| `numcolonies` | N/A | N/A | N/A | ✓ | ✓ | Number of colonies |
| `numacs` | N/A | N/A | N/A | ✓ | ✓ | Number of ACS colonies |
| `q0` | ✓ | ✗ | ✓ | ✓ | ✓ | Exploitation parameter |
| `rho` | ✓ | ✗ | ✓ | ✓ | ✓ | Pheromone persistence |
| `bve` | ✓ | ✗ | ✓ | ✓ | ✓ | Evaporation rate |
| `timeout` | ✓ | ✓ | ✓ | ✓ | ✓ | Timeout in seconds |
| `success_rate` | ✓ | ✓ | ✓ | ✓ | ✓ | Percentage of solved instances |
| `time_mean` | ✓ | ✓ | ✓ | ✓ | ✓ | Mean solve time (seconds) |
| `time_std` | ✓ | ✓ | ✓ | ✓ | ✓ | Standard deviation of solve time |
| `iter_mean` | ✓ | N/A | ✓ | ✓ | ✓ | Mean iterations |
| `with_comm` | N/A | N/A | ✓ | N/A | ✓ | Runs with thread communication |
| `without_comm` | N/A | N/A | ✓ | N/A | ✓ | Runs without thread communication |
| `cp_initial_mean` | ✓ | ✓ | ✓ | ✓ | ✓ | Mean initial constraint propagation time |
| `cp_ant_mean` | ✓ | ✗ | ✓ | ✓ | ✓ | Mean ant constraint propagation time |
| `ant_guessing_mean` | ✓ | ✗ | ✓ | ✓ | ✓ | Mean ant decision-making time |
| `coop_game_mean` | N/A | N/A | N/A | ✓ | ✓ | Mean cooperative game theory time |
| `pheromone_fusion_mean` | N/A | N/A | N/A | ✓ | ✓ | Mean pheromone fusion time |
| `public_path_mean` | N/A | N/A | N/A | ✓ | ✓ | Mean public path recommendation time |
| `communication_time_mean` | N/A | N/A | ✓ | N/A | ✓ | Mean thread communication time |
| `cp_total_mean` | ✓ | ✓ | ✓ | ✓ | ✓ | Total CP time (initial + ant) |
| `cp_percentage` | ✓ | ✓ | ✓ | ✓ | ✓ | CP time as % of total time |

**Legend:**
- ✓ = Available
- ✗ = Not applicable (algorithm doesn't use this)
- N/A = Shown as "N/A" in CSV

---

## Understanding the Results

### Console Output

During execution, you'll see:

```
============================================================
Running Algorithm 0
============================================================

[alg 0] [1/100] instances/paquita-database/p01.txt -> OK (CP_init=0.000123s (0.12%), CP_ant=0.001234s (1.23%), AntGuess=0.002345s (2.35%), Total=0.100000s, 150 iter)
[alg 0] [2/100] instances/paquita-database/p02.txt -> OK (...)
...

============================================================
Running Algorithm 2
============================================================

[alg 2] [1/100] instances/paquita-database/p01.txt -> OK (...)
...

============================================================
===== Summary =====
Solver binary   : x64/Release/sudoku_ants.exe
Instances folder: C:\...\instances\paquita-database
Output CSV      : C:\...\results\Run_9x9_20260123_143052.csv

--- Algorithm 0 ---
Ants            : 10
q0              : 0.9
rho             : 0.9
bve             : 0.005
Timeout         : 120.0s
Total puzzles   : 100
Succeeded       : 98
Failed          : 2
Average time    : 1.23456 s
Average iters   : 150.23

--- Algorithm 2 ---
Ants            : 10
Threads         : 4
q0              : 0.9
rho             : 0.9
bve             : 0.005
Timeout         : 120.0s
Total puzzles   : 100
Succeeded       : 100
Failed          : 0
Average time    : 0.98765 s
Average iters   : 120.45
With comm       : 45/100 (45.0%)
============================================================
```

### Timing Breakdown

For algorithms 0, 2, 3, and 4, detailed timing is shown:

- **CP_init**: Initial constraint propagation time
- **CP_ant**: Constraint propagation during ant construction
- **AntGuess**: Time spent in ant decision-making
- **CoopGame**: Cooperative game theory allocation time (alg 3, 4)
- **PherFusion**: Pheromone fusion time (alg 3, 4)
- **PublicPath**: Public path recommendation time (alg 3, 4)
- **CommTime**: Thread communication time (alg 2, 4)
- **Total**: Total solve time
- **Percentages**: Each component as % of total time

### Success Rate

- **100%**: All instances solved within timeout
- **< 100%**: Some instances timed out or failed
- Failed instances still contribute to statistics (time = timeout value)

### Communication Statistics (Algorithms 2 & 4)

- **With comm**: Number of runs where threads communicated
- **Without comm**: Number of runs where threads didn't communicate
- Higher communication rate may indicate more difficult instances

---

## Tips and Best Practices

### 1. Start Small
Always test with `--single-instance` before running full batches:
```bash
python scripts/run_general.py --single-instance --alg 0 2 4
```

### 2. Use Appropriate Timeouts
- 9x9 puzzles: 60-120 seconds usually sufficient
- 16x16 puzzles: 300-600 seconds recommended
- 25x25+ puzzles: 1800+ seconds may be needed

### 3. Thread Count Selection
- Use `--threads` equal to your CPU core count for best performance
- For hyper-threaded CPUs, test both physical and logical core counts

### 4. Multi-Colony Configuration
- `--numacs` should be less than `--numcolonies`
- Default ratio: 3 ACS colonies + 1 MMAS colony = 4 total colonies
- Experiment with different ratios for your problem set

### 5. Output Organization
Let the script auto-generate filenames to avoid overwriting:
```bash
# Good: Each run gets unique timestamp
python scripts/run_general.py --alg 0 2 4

# Risk: Might overwrite previous results
python scripts/run_general.py --alg 0 2 4 --output results.csv
```

### 6. Batch Experiments
Use shell loops for parameter sweeps:
```bash
# PowerShell
foreach ($ants in 5,10,15,20) {
    python scripts/run_general.py --alg 0 --ants $ants
}

# Bash
for ants in 5 10 15 20; do
    python scripts/run_general.py --alg 0 --ants $ants
done
```

### 7. Monitor Progress
Keep `--verbose` enabled (default) to monitor progress and detect issues early

### 8. CSV Analysis
Import the CSV into Excel, Python (pandas), or R for analysis:
```python
import pandas as pd
df = pd.read_csv('results/Run_9x9_20260123_143052.csv')
print(df[['puzzle_size', 'time_mean_alg0', 'time_mean_alg2', 'time_mean_alg4']])
```

---

## Troubleshooting

### Solver Not Found
```
Error: Could not find solver executable
```
**Solution**: Specify solver path explicitly:
```bash
python scripts/run_general.py --solver path/to/sudoku_ants.exe
```

### No Instances Found
```
No instances found in 'path/to/instances'
```
**Solution**: Check path and ensure `.txt` files exist in the directory

### Timeout Issues
If many instances are timing out:
- Increase `--timeout` value
- Try algorithm 2 (parallel) for better performance
- Check if puzzle difficulty matches your timeout expectations

### Memory Issues
For large batch runs:
- Use `--limit` to process in smaller batches
- Close other applications
- Monitor system resources

---

## Examples by Use Case

### Research Paper Experiments
```bash
# Comprehensive comparison
python scripts/run_general.py \
    --alg 0 2 3 4 \
    --instances-root instances/paquita-database \
    --ants 10 \
    --threads 4 \
    --numacs 3 \
    --numcolonies 4 \
    --timeout 300.0
```

### Performance Benchmarking
```bash
# Test scalability
python scripts/run_general.py \
    --alg 2 4 \
    --threads 8 \
    --instances-root instances/16x16-database \
    --timeout 600.0
```

### Algorithm Development
```bash
# Quick iteration testing
python scripts/run_general.py \
    --single-instance \
    --alg 3 \
    --solver-verbose \
    --instances-root instances/logic-solvable
```

### Production Solving
```bash
# Solve all instances with best-performing algorithm
python scripts/run_general.py \
    --alg 2 \
    --threads 8 \
    --ants 15 \
    --timeout 300.0 \
    --instances-root instances/my-puzzles
```

---

## Additional Resources

- **Solver Documentation**: See `src/solvermain.cpp` for solver implementation details
- **Timing Documentation**: See `TIMING_DOCUMENTATION.md` for timing component explanations
- **Algorithm Papers**: Refer to the research papers for theoretical background on each algorithm

---

## Version History

- **v2.0** (2026-01-23): Added multi-algorithm support, wide-format CSV, dynamic filenames
- **v1.0**: Initial version with single-algorithm support

---

For questions or issues, please refer to the project repository or contact the development team.
