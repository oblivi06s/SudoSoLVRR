# Timing Documentation

## Overview

The solver tracks detailed timing information for various operations during the solving process. However, the sum of all explicitly tracked times may not exactly equal the **Total Solve Time** due to overhead operations that are not individually instrumented.

## Tracked Time Components

The following time components are explicitly tracked and displayed:

### 1. Initial CP Time
- **When**: Before the solver's `Solve()` method is called
- **What**: Time spent applying constraint propagation to the initial puzzle
- **Location**: `solvermain.cpp` - initial constraint propagation phase

### 2. Ant CP Time
- **When**: During ant solution construction
- **What**: Time spent in constraint propagation operations when ants set cells
- **Location**: `colonyant.cpp`, `sudokuant.cpp` - `SetCellAndPropagate()` calls
- **Note**: For multi-threaded algorithms (2 & 4), this is the CP time from the **winning thread**

### 3. Ant Guessing Time
- **When**: During ant solution construction
- **What**: Time spent by ants making decisions (evaluating pheromone, selecting values via greedy or roulette selection)
- **Location**: `colonyant.cpp`, `sudokuant.cpp` - decision-making logic in `StepSolution()`
- **Note**: For multi-threaded algorithms (2 & 4), this is the guessing time from the **winning thread**

### 4. Cooperative Game Time (Algorithms 3 & 4 only)
- **When**: During each iteration
- **What**: Time spent in cooperative game theory allocation for ACS colonies
- **Location**: `multicolonyantsystem.cpp` - `ACSCooperativeGameAllocate()`

### 5. Pheromone Fusion Time (Algorithms 3 & 4 only)
- **When**: During each iteration
- **What**: Time spent fusing pheromone matrices from different colonies
- **Location**: `multicolonyantsystem.cpp` - `ApplyPheromoneFusion()`

### 6. Public Path Recommendation Time (Algorithms 3 & 4 only)
- **When**: During each iteration
- **What**: Time spent applying public path recommendations to colonies
- **Location**: `multicolonyantsystem.cpp` - `ApplyPublicPathRecommendation()`

### 7. Communication Between Threads Time (Algorithms 2 & 4 only)
- **When**: During periodic synchronization phases
- **What**: Time spent in barrier synchronization and solution exchange between threads
- **Location**: 
  - `parallelsudokuantsystem.cpp` - `PerformBarrierSynchronization()`
  - `multithreadmulticolonyantsystem.cpp` - `PerformBarrierSynchronization()`
- **Note**: This is the communication time from the **winning thread**

## Why the Sum May Not Equal Total Solve Time

The **Total Solve Time** (`solTime`) is measured from when `solutionTimer.Reset()` is called at the start of `Solve()` until the solution is found or timeout occurs. This includes:

### Tracked Operations (explicitly timed):
- ✅ Initial CP operations
- ✅ Ant CP operations
- ✅ Ant decision-making (guessing)
- ✅ Cooperative game theory (algorithms 3 & 4)
- ✅ Pheromone fusion (algorithms 3 & 4)
- ✅ Public path recommendation (algorithms 3 & 4)
- ✅ Thread communication (algorithms 2 & 4)

### Untracked Overhead (not explicitly timed):
- ❌ **Iteration loop overhead**: Condition checks, counter increments, loop control
- ❌ **Finding iteration-best ant**: Searching through ant solutions to find the best
- ❌ **Standard pheromone updates**: Global pheromone update operations (not fusion/coop game)
- ❌ **Pheromone initialization**: Setting up initial pheromone matrices
- ❌ **Solution copying**: Copying best solutions between data structures
- ❌ **Timeout checks**: Periodic time checks during iterations
- ❌ **Thread management**: Thread creation, joining, synchronization overhead (for multi-threaded)
- ❌ **Memory operations**: Allocations, deallocations, data structure operations
- ❌ **Other solver logic**: Any other operations not explicitly instrumented

## Example Calculation

```
Total Solve Time = Initial CP Time + Ant CP Time + Ant Guessing Time 
                 + [Coop Game Time] + [Pheromone Fusion Time] 
                 + [Public Path Time] + [Communication Time]
                 + Overhead (untracked)
```

Where:
- `[Coop Game Time]`, `[Pheromone Fusion Time]`, `[Public Path Time]` are only for algorithms 3 & 4
- `[Communication Time]` is only for algorithms 2 & 4
- `Overhead` represents all untracked operations

## Notes

1. **Winning Thread**: For multi-threaded algorithms (2 & 4), most timing values are taken from the thread that found the best solution, not aggregated across all threads.

2. **Initial CP Time**: This is added to `solTime` after the solver completes, so it's included in the total but measured separately.

3. **Precision**: Timing measurements use `std::chrono::steady_clock` with microsecond precision, but accumulated times may have small rounding differences.

4. **Algorithm-Specific Timing**:
   - **Algorithm 0** (Single-threaded ACS): Initial CP, Ant CP, Ant Guessing
   - **Algorithm 2** (Parallel ACS): Initial CP, Ant CP (winning thread), Ant Guessing (winning thread), Communication (winning thread)
   - **Algorithm 3** (Multi-colony): Initial CP, Ant CP, Ant Guessing, Coop Game, Pheromone Fusion, Public Path
   - **Algorithm 4** (Multi-threaded Multi-colony): All of Algorithm 3 + Communication (all from winning thread)

## Conclusion

The difference between the sum of tracked times and the total solve time represents the overhead of operations that are not explicitly instrumented. This is expected and normal behavior. The tracked times provide insight into the major computational components, while the overhead accounts for the remaining solver operations.
