# Ant Count Parameters - Feature Documentation

## Overview

The `run_general.py` script now supports algorithm-specific ant count configuration, allowing different numbers of ants for single-colony vs multi-colony algorithms.

---

## Problem Statement

Previously, all algorithms used the same `--ants` parameter. However:
- **Single-colony algorithms (0, 2)** often perform well with fewer ants
- **Multi-colony algorithms (3, 4)** typically benefit from more ants per colony

This made fair comparisons difficult when running multiple algorithms simultaneously.

---

## Solution

Added two new optional parameters:
- `--ants-single`: Ant count for algorithms 0 and 2
- `--ants-multi`: Ant count for algorithms 3 and 4

The existing `--ants` parameter serves as a global fallback.

---

## Parameter Logic

### Priority Order

**For Algorithms 0 and 2 (Single-Colony):**
```
--ants-single → --ants → 10 (default)
```

**For Algorithms 3 and 4 (Multi-Colony):**
```
--ants-multi → --ants → 10 (default)
```

### Decision Tree

```
Is algorithm 0 or 2?
├─ Yes: Is --ants-single specified?
│   ├─ Yes: Use --ants-single
│   └─ No: Is --ants specified?
│       ├─ Yes: Use --ants
│       └─ No: Use 10 (default)
└─ No: Is algorithm 3 or 4?
    └─ Yes: Is --ants-multi specified?
        ├─ Yes: Use --ants-multi
        └─ No: Is --ants specified?
            ├─ Yes: Use --ants
            └─ No: Use 10 (default)
```

---

## Usage Examples

### Example 1: All Algorithms Same Count
```bash
python scripts/run_general.py --alg 0 2 3 4 --ants 10
```
**Result:**
- Alg 0: 10 ants
- Alg 2: 10 ants
- Alg 3: 10 ants
- Alg 4: 10 ants

---

### Example 2: Different Counts for Single vs Multi
```bash
python scripts/run_general.py --alg 0 2 3 4 \
    --ants-single 3 \
    --ants-multi 10
```
**Result:**
- Alg 0: 3 ants
- Alg 2: 3 ants
- Alg 3: 10 ants
- Alg 4: 10 ants

---

### Example 3: Override Single-Colony Only
```bash
python scripts/run_general.py --alg 0 2 3 4 \
    --ants 15 \
    --ants-single 3
```
**Result:**
- Alg 0: 3 ants (overridden)
- Alg 2: 3 ants (overridden)
- Alg 3: 15 ants (from --ants)
- Alg 4: 15 ants (from --ants)

---

### Example 4: Your Original Request
```bash
python scripts/run_general.py \
    --instances-root instances/paquita-database \
    --alg 0 3 4 \
    --ants-single 3 \
    --ants-multi 10 \
    --threads 3 \
    --numacs 2 \
    --numcolonies 3 \
    --timeout 5
```
**Result:**
- Alg 0: 3 ants
- Alg 3: 10 ants
- Alg 4: 10 ants (with 3 threads)

---

## Implementation Details

### Code Changes

**1. Argument Parser (lines 533-537)**
```python
parser.add_argument("--ants", type=int, default=None, 
    help="Override number of ants for all algorithms (default: 10). Can be overridden by --ants-single or --ants-multi.")
parser.add_argument("--ants-single", type=int, default=None, 
    help="Number of ants for single-colony algorithms (alg 0 and 2). Overrides --ants for these algorithms.")
parser.add_argument("--ants-multi", type=int, default=None, 
    help="Number of ants for multi-colony algorithms (alg 3 and 4). Overrides --ants for these algorithms.")
```

**2. Command Builder (lines 177-191)**
```python
# Determine ant count based on algorithm
ant_count = None
if algorithm in [0, 2]:
    ant_count = args.ants_single if args.ants_single is not None else args.ants
elif algorithm in [3, 4]:
    ant_count = args.ants_multi if args.ants_multi is not None else args.ants

if ant_count is not None:
    cmd.extend(("--ants", str(ant_count)))
```

**3. CSV Output (lines 797-810)**
```python
# Get actual parameter values based on algorithm
if alg in [0, 2]:
    actual_ants = args.ants_single if args.ants_single is not None else (args.ants if args.ants is not None else 10)
elif alg in [3, 4]:
    actual_ants = args.ants_multi if args.ants_multi is not None else (args.ants if args.ants is not None else 10)
else:
    actual_ants = args.ants if args.ants is not None else 10
```

**4. Summary Output (lines 872-889)**
Similar logic for displaying ant counts in the summary.

---

## Backward Compatibility

✅ **Fully backward compatible**

Existing scripts using `--ants` will continue to work exactly as before:
```bash
# Old usage still works
python scripts/run_general.py --alg 0 --ants 10
```

The new parameters are **optional** and only used when specified.

---

## CSV Output

The CSV output correctly reflects the ant count used for each algorithm:

**Example CSV Row:**
```csv
puzzle_size,nAnts_alg0,nAnts_alg2,nAnts_alg3,nAnts_alg4,...
9x9,3,3,10,10,...
```

When `--ants-single 3` and `--ants-multi 10` are used.

---

## Summary Output

The console summary also shows the correct ant count per algorithm:

```
--- Algorithm 0 ---
Ants            : 3
q0              : 0.9
...

--- Algorithm 3 ---
Ants            : 10
Num Colonies    : 3
...
```

---

## Testing

### Test Case 1: Default Behavior
```bash
python scripts/run_general.py --alg 0 2 3 4 --single-instance
```
**Expected:** All algorithms use 10 ants (default)

### Test Case 2: Global Override
```bash
python scripts/run_general.py --alg 0 2 3 4 --ants 20 --single-instance
```
**Expected:** All algorithms use 20 ants

### Test Case 3: Specific Overrides
```bash
python scripts/run_general.py --alg 0 2 3 4 --ants-single 5 --ants-multi 15 --single-instance
```
**Expected:** Alg 0,2 use 5 ants; Alg 3,4 use 15 ants

### Test Case 4: Mixed Configuration
```bash
python scripts/run_general.py --alg 0 2 3 4 --ants 12 --ants-single 4 --single-instance
```
**Expected:** Alg 0,2 use 4 ants; Alg 3,4 use 12 ants

---

## Related Parameters

### Other Algorithm-Grouped Parameters

**Threads** (shared by alg 2 and 4):
```bash
--threads 8  # Used by both algorithm 2 and 4
```

**Multi-Colony Parameters** (shared by alg 3 and 4):
```bash
--numacs 3         # Number of ACS colonies
--numcolonies 4    # Total colonies (ACS + MMAS)
```

These remain unchanged as they already have the desired grouping behavior.

---

## Benefits

1. **Fair Comparisons**: Different algorithm types can use appropriate ant counts
2. **Flexibility**: Fine-grained control over parameters
3. **Backward Compatible**: Existing scripts continue to work
4. **Intuitive**: Clear naming (`-single` vs `-multi`)
5. **Fallback Logic**: Sensible defaults at every level

---

## Future Enhancements

Potential future additions:
- Algorithm-specific `q0`, `rho`, `evap` parameters
- Configuration file support for complex parameter sets
- Parameter presets (e.g., `--preset fast`, `--preset thorough`)

---

## Version History

- **v2.1** (2026-01-23): Added `--ants-single` and `--ants-multi` parameters
- **v2.0** (2026-01-23): Multi-algorithm support with wide-format CSV
- **v1.0**: Initial version

---

## See Also

- [RUN_GENERAL_GUIDE.md](RUN_GENERAL_GUIDE.md) - Complete usage guide
- [SOLVERMAIN_REFACTORING_COMPLETED.md](SOLVERMAIN_REFACTORING_COMPLETED.md) - Solver improvements
- [TIMING_DOCUMENTATION.md](../TIMING_DOCUMENTATION.md) - Timing component explanations
