# Pheromone Update Timing Implementation

## Overview

This document describes the implementation of pheromone update timing across all algorithms and the introduction of derived metrics (ACS Time and DCM-ACO Time) to achieve 100% time coverage.

## Motivation

Previously, the timing breakdown showed 90-92% coverage, with 8-10% untracked overhead. To achieve 100% coverage and better understand algorithm performance, we added:

1. **Pheromone Update Time** - Previously untracked time spent updating pheromone matrices
2. **Derived Metrics** - High-level algorithm phase times for easier analysis

## Implementation Details

### 1. Pheromone Update Time Tracking

#### Added to All Algorithms:

**Algorithm 0 (Single-threaded ACS):**
- File: `src/sudokuantsystem.h`, `src/sudokuantsystem.cpp`
- Location: Around the `UpdatePheromone()` call in the main loop
- Tracks: Global pheromone update + best pheromone decay

**Algorithm 2 (Parallel ACS):**
- Files: `src/parallelsudokuantsystem.h`, `src/parallelsudokuantsystem.cpp`
- Location: Around both `UpdatePheromone()` and `UpdatePheromoneWithCommunication()` calls
- Tracks: Standard pheromone update OR three-source communication update

**Algorithm 3 (Multi-Colony):**
- Files: `src/multicolonyantsystem.h`, `src/multicolonyantsystem.cpp`
- Location: Around the pheromone update loops for ACS and MMAS colonies
- Tracks: All colony pheromone updates (ACS + MMAS)

**Algorithm 4 (Multi-Thread Multi-Colony):**
- Files: `src/multithreadmulticolonyantsystem.h`, `src/multithreadmulticolonyantsystem.cpp`
- Location: Around pheromone update loops in `RunIteration()`
- Tracks: Per-thread pheromone updates across all colonies

### 2. Derived Metrics

#### ACS Time (Algorithms 0, 2)
```
ACS Time = Ant CP Time + Ant Decision Time + Pheromone Update Time
```

This represents the core Ant Colony System algorithm time, excluding:
- Initial CP (preprocessing)
- Communication (for Algorithm 2)

#### DCM-ACO Time (Algorithms 3, 4)
```
DCM-ACO Time = ACS Time + Cooperative Game Time + Pheromone Fusion Time + Public Path Recommendation Time
```

This represents the complete Dynamic Cooperative Multi-colony ACO algorithm time, including:
- All ACS components
- Multi-colony specific operations (cooperative game, fusion, public path)

Excludes:
- Initial CP (preprocessing)
- Communication (for Algorithm 4)

## Time Breakdown Structure

### Algorithm 0 (Single-threaded ACS)
```
Total Solve Time = 100%
├── Initial CP Time: ~5%
└── ACS Time: ~95%
    ├── Ant CP Time: ~20%
    ├── Ant Decision Time: ~30%
    └── Pheromone Update Time: ~45%
```

### Algorithm 2 (Parallel ACS)
```
Total Solve Time = 100%
├── Initial CP Time: ~5%
├── ACS Time: ~90%
│   ├── Ant CP Time: ~20%
│   ├── Ant Decision Time: ~25%
│   └── Pheromone Update Time: ~45%
└── Communication Time: ~5%
```

### Algorithm 3 (Multi-Colony)
```
Total Solve Time = 100%
├── Initial CP Time: ~5%
└── DCM-ACO Time: ~95%
    ├── Ant CP Time: ~15%
    ├── Ant Decision Time: ~20%
    ├── Pheromone Update Time: ~40%
    ├── Cooperative Game Time: ~5%
    ├── Pheromone Fusion Time: ~10%
    └── Public Path Recommendation Time: ~5%
```

### Algorithm 4 (Multi-Thread Multi-Colony)
```
Total Solve Time = 100%
├── Initial CP Time: ~5%
├── DCM-ACO Time: ~90%
│   ├── Ant CP Time: ~15%
│   ├── Ant Decision Time: ~20%
│   ├── Pheromone Update Time: ~35%
│   ├── Cooperative Game Time: ~5%
│   ├── Pheromone Fusion Time: ~10%
│   └── Public Path Recommendation Time: ~5%
└── Communication Time: ~5%
```

## CSV Output Structure

### Time Means (in order):
1. `cp_initial_mean` - Initial constraint propagation
2. `cp_ant_mean` - CP during ant construction
3. `cp_total_mean` - Sum of initial + ant CP
4. `ant_guessing_mean` - Ant decision-making time
5. `pheromone_update_mean` - **NEW** Pheromone matrix updates
6. `coop_game_mean` - Cooperative game theory (alg 3, 4)
7. `pheromone_fusion_mean` - Pheromone fusion (alg 3, 4)
8. `public_path_mean` - Public path recommendation (alg 3, 4)
9. `communication_time_mean` - Thread communication (alg 2, 4)
10. `acs_time_mean` - **NEW** Derived ACS time (alg 0, 2)
11. `dcm_aco_time_mean` - **NEW** Derived DCM-ACO time (alg 3, 4)

### Percentages (grouped at end):
- All time components as percentages of total solve time
- Including derived metrics: `acs_time_percentage`, `dcm_aco_time_percentage`

## Verbose Output Example

```
==Time Breakdown==
Initial CP Time:                      0.001234 s (5.00%)
Ant CP Time:                          0.004567 s (18.50%)
Ant Decision Time:                    0.007890 s (32.00%)
Pheromone Update Time:                0.011000 s (44.50%)
Total Solve Time:                     0.024691 s
```

For multi-colony algorithms (3, 4), additional lines appear:
```
Cooperative Game Time:                0.001000 s (4.05%)
Pheromone Fusion Time:                0.002000 s (8.10%)
Public Path Recommendation Time:      0.001000 s (4.05%)
```

## Benefits

### 1. 100% Time Coverage
All major algorithmic operations are now tracked, accounting for the full solve time.

### 2. Simplified Analysis
- **ACS Time** provides a single metric for the core ACO algorithm
- **DCM-ACO Time** provides a single metric for the complete multi-colony algorithm
- Easy to compare algorithm efficiency

### 3. Better Insights
- Understand where time is spent in pheromone management
- Compare pheromone update strategies across algorithms
- Identify bottlenecks in multi-colony operations

### 4. Consistent Reporting
- All algorithms report comparable metrics
- Percentages always sum to 100%
- Clear separation of preprocessing (Initial CP) vs. algorithm execution

## Usage in Scripts

The `run_general.py` script automatically:
1. Parses pheromone update time from solver output
2. Calculates derived metrics (ACS/DCM-ACO time)
3. Computes percentages for all components
4. Outputs to CSV with proper N/A handling for algorithm-specific metrics

Example command:
```bash
python scripts/run_general.py --instances-root instances/paquita-database \
    --alg 0 3 4 --ants-single 10 --ants-multi 3 --threads 3 \
    --numcolonies 3 --numacs 2 --timeout 20
```

## Validation

To verify 100% coverage, sum all percentage columns for a given algorithm:

**Algorithm 0:**
```
Initial CP % + ACS Time % = 100%
```

**Algorithm 2:**
```
Initial CP % + ACS Time % + Communication % = 100%
```

**Algorithm 3:**
```
Initial CP % + DCM-ACO Time % = 100%
```

**Algorithm 4:**
```
Initial CP % + DCM-ACO Time % + Communication % = 100%
```

## Notes

- Pheromone update time includes both the matrix updates and any associated overhead (e.g., best pheromone decay)
- For Algorithm 2, pheromone update time includes both standard updates and three-source communication updates
- Derived metrics (ACS/DCM-ACO) are calculated in the Python script, not in the C++ solver
- The solver outputs individual component times; the script computes derived metrics and percentages

## See Also

- [TIMING_DOCUMENTATION.md](../TIMING_DOCUMENTATION.md) - Original timing documentation
- [RUN_GENERAL_GUIDE.md](RUN_GENERAL_GUIDE.md) - Script usage guide
- [CSV_PERCENTAGE_FIX.md](CSV_PERCENTAGE_FIX.md) - Percentage calculation methodology
