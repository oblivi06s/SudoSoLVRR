# CSV Percentage Calculation Fix

## Issues Fixed

### Issue 1: Ant Decision Time Always Showing 0

**Problem:** The regex pattern was incorrectly matching "Ant Decision Time" and assigning it to the `cp_ant` variable instead of `ant_guessing_time`.

**Root Cause:**
```python
# Line 306 - WRONG pattern
ant_cp_match = re.search(r"Ant (?:CP|Decision) Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
```

This pattern matched both "Ant CP Time" AND "Ant Decision Time", so when it encountered "Ant Decision Time", it overwrote the CP time value, and the later pattern for ant_guessing_time never matched.

**Fix:**
```python
# Now only matches "Ant CP Time"
ant_cp_match = re.search(r"Ant CP Time:\s*([0-9]*\.?[0-9]+)\s+s", line)
```

---

### Issue 2: CP Percentage Exceeding 100%

**Problem:** Percentages were calculated by averaging times separately, then computing the percentage. This is mathematically incorrect because it doesn't properly weight runs by their duration.

**Example of the Problem:**
```
Run 1: CP = 1.5s, Total = 8.0s
Run 2: CP = 2.5s, Total = 12.0s

WRONG Way (averaging means):
  Average CP = (1.5 + 2.5) / 2 = 2.0s
  Average Total = (8.0 + 12.0) / 2 = 10.0s
  Percentage = (2.0 / 10.0) × 100 = 20.00%

ALSO WRONG (averaging percentages):
  Run 1 Percentage = (1.5 / 8.0) × 100 = 18.75%
  Run 2 Percentage = (2.5 / 12.0) × 100 = 20.83%
  Average Percentage = (18.75 + 20.83) / 2 = 19.79%
  (This treats a 8s run and 12s run equally, which is incorrect)

CORRECT Way (sum then divide):
  Sum CP = 1.5 + 2.5 = 4.0s
  Sum Total = 8.0 + 12.0 = 20.0s
  Percentage = (4.0 / 20.0) × 100 = 20.00%
  (This correctly weights by actual time spent)
```

**Why the correct way is better:** When you want to know "what percentage of total time is spent on CP across all runs", you should sum all times first, then calculate the percentage. This gives the overall proportion and correctly weights longer runs more heavily than shorter runs.

**Fix:** Calculate percentages by summing all component times and all total times, then dividing:

```python
# Calculate percentages correctly: sum all times, then compute percentage
# This gives the overall proportion of time spent on each component
cp_initial_sum = sum(stats["cp_initial"]) if stats["cp_initial"] else 0
cp_ant_sum = sum(stats["cp_ant"]) if stats["cp_ant"] else 0
ant_guessing_sum = sum(stats["ant_guessing"]) if stats["ant_guessing"] else 0
coop_game_sum = sum(stats["coop_game"]) if stats["coop_game"] else 0
pheromone_fusion_sum = sum(stats["pheromone_fusion"]) if stats["pheromone_fusion"] else 0
public_path_sum = sum(stats["public_path"]) if stats["public_path"] else 0
communication_time_sum = sum(stats["communication_time"]) if stats["communication_time"] else 0
time_sum = sum(stats["times"]) if stats["times"] else 0

# Calculate percentages from sums
cp_initial_percentage = (cp_initial_sum / time_sum * 100) if time_sum > 0 else 0
cp_ant_percentage = (cp_ant_sum / time_sum * 100) if time_sum > 0 else 0
ant_guessing_percentage = (ant_guessing_sum / time_sum * 100) if time_sum > 0 else 0
coop_game_percentage = (coop_game_sum / time_sum * 100) if time_sum > 0 else 0
pheromone_fusion_percentage = (pheromone_fusion_sum / time_sum * 100) if time_sum > 0 else 0
public_path_percentage = (public_path_sum / time_sum * 100) if time_sum > 0 else 0
communication_time_percentage = (communication_time_sum / time_sum * 100) if time_sum > 0 else 0
cp_percentage = ((cp_initial_sum + cp_ant_sum) / time_sum * 100) if time_sum > 0 else 0
```

This fix was applied to ALL timing components:
- Initial CP Time
- Ant CP Time
- Ant Decision Time (Ant Guessing)
- Cooperative Game Time
- Pheromone Fusion Time
- Public Path Recommendation Time
- Communication Time
- Total CP Time

---

## New CSV Structure

### Column Organization

Columns are now organized with **time and percentage side-by-side** for easy comparison:

```csv
puzzle_size,
nAnts_alg0, nAnts_alg3, nAnts_alg4,
...,
cp_initial_mean_alg0, cp_initial_mean_alg3, cp_initial_mean_alg4,
cp_initial_percentage_alg0, cp_initial_percentage_alg3, cp_initial_percentage_alg4,
cp_ant_mean_alg0, cp_ant_mean_alg3, cp_ant_mean_alg4,
cp_ant_percentage_alg0, cp_ant_percentage_alg3, cp_ant_percentage_alg4,
ant_guessing_mean_alg0, ant_guessing_mean_alg3, ant_guessing_mean_alg4,
ant_guessing_percentage_alg0, ant_guessing_percentage_alg3, ant_guessing_percentage_alg4,
...
```

### New Columns Added

For each algorithm, the following percentage columns were added:
- `cp_initial_percentage_alg{X}` - Initial CP time as % of total
- `cp_ant_percentage_alg{X}` - Ant CP time as % of total
- `ant_guessing_percentage_alg{X}` - Ant decision time as % of total
- `coop_game_percentage_alg{X}` - Cooperative game time as % of total (alg 3, 4)
- `pheromone_fusion_percentage_alg{X}` - Pheromone fusion time as % of total (alg 3, 4)
- `public_path_percentage_alg{X}` - Public path recommendation time as % of total (alg 3, 4)
- `communication_time_percentage_alg{X}` - Communication time as % of total (alg 2, 4)

---

## Benefits

### 1. Accurate Percentages
Percentages now correctly represent the average proportion of time spent in each component, accounting for variation across instances.

### 2. Easy Comparison in Excel
Time and percentage are side-by-side, making it easy to see both absolute and relative performance:

```
cp_initial_mean_alg0: 0.001234
cp_initial_percentage_alg0: 12.34
```

### 3. Proper N/A Handling
Percentages for non-applicable components (e.g., cooperative game time for algorithm 0) are marked as "N/A".

### 4. Validation
Percentages should now always be ≤ 100% (unless there's a timing bug in the solver itself).

---

## Example Output

### Before Fix:
```csv
puzzle_size,cp_initial_mean_alg0,cp_ant_mean_alg0,ant_guessing_mean_alg0,cp_percentage_alg0
16x16,0.001234,0.005678,0.000000,324.56
```

Issues:
- `ant_guessing_mean` = 0 (wrong!)
- `cp_percentage` = 324.56% (impossible!)

### After Fix:
```csv
puzzle_size,cp_initial_mean_alg0,cp_initial_percentage_alg0,cp_ant_mean_alg0,cp_ant_percentage_alg0,ant_guessing_mean_alg0,ant_guessing_percentage_alg0,cp_percentage_alg0
16x16,0.001234,12.34,0.005678,56.78,0.002345,23.45,69.12
```

Benefits:
- `ant_guessing_mean` has correct value
- All percentages are realistic (< 100%)
- Time and percentage are paired for easy comparison

---

## Testing Recommendations

### 1. Verify Ant Decision Time
Check that `ant_guessing_mean` values are non-zero for algorithms 0, 2, 3, and 4.

### 2. Verify Percentages
Sum of all component percentages should be < 100% (the remainder is untracked overhead).

Example check:
```
cp_initial_percentage + cp_ant_percentage + ant_guessing_percentage + 
coop_game_percentage + pheromone_fusion_percentage + public_path_percentage + 
communication_time_percentage < 100%
```

### 3. Compare Across Algorithms
Percentages should be comparable across algorithms even if absolute times differ.

---

## Files Modified

- `scripts/run_general.py`:
  - Line ~306: Fixed Ant Decision Time regex pattern
  - Line ~387-420: Updated CSV column headers to include percentages
  - Line ~821-890: Added percentage calculation helper function and computed all percentages correctly

---

## Version History

- **v2.2** (2026-01-24): Fixed percentage calculations and ant decision time parsing
- **v2.1** (2026-01-23): Added `--ants-single` and `--ants-multi` parameters
- **v2.0** (2026-01-23): Multi-algorithm support with wide-format CSV

---

## See Also

- [RUN_GENERAL_GUIDE.md](RUN_GENERAL_GUIDE.md) - Complete usage guide
- [ANT_COUNT_PARAMETERS.md](ANT_COUNT_PARAMETERS.md) - Ant count parameter documentation
- [TIMING_DOCUMENTATION.md](../TIMING_DOCUMENTATION.md) - Timing component explanations
