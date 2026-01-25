# Run Multiple - Documentation

## Overview

These scripts automate running the Sudoku solver multiple times with the same configuration, saving each run to a separate CSV file.

---

## Available Scripts

### 1. **PowerShell** (Windows - Recommended)
**File:** `scripts/run_multiple.ps1`

**Usage:**
```

```

### 2. **Batch** (Windows - Alternative)
**File:** `scripts/run_multiple.bat`

**Usage:**
```cmd
scripts\run_multiple.bat
```

### 3. **Bash** (Linux/Mac)
**File:** `scripts/run_multiple.sh`

**Usage:**
```bash
bash scripts/run_multiple.sh
```

---

## Default Configuration

The scripts are currently configured to run:

```
Number of Runs: 5
Instances: instances/16x16-database
Algorithms: 0 3 4
Ants (Single): 10
Ants (Multi): 3
Num ACS: 2
Num Colonies: 3
Threads: 3
Timeout: 20 seconds
Output Directory: results/For_16x16/
Output Files: Run_1.csv, Run_2.csv, Run_3.csv, Run_4.csv, Run_5.csv
```

---

## Customizing the Configuration

### PowerShell (`run_multiple.ps1`)

Edit the configuration section at the top:

```powershell
# Configuration
$NumRuns = 5                              # Number of times to run
$InstancesRoot = "instances/16x16-database"  # Instance folder
$Algorithms = "0 3 4"                     # Algorithms to run
$AntsSingle = 10                          # Ants for alg 0,2
$AntsMulti = 3                            # Ants for alg 3,4
$NumACS = 2                               # ACS colonies
$NumColonies = 3                          # Total colonies
$Threads = 3                              # Number of threads
$Timeout = 20                             # Timeout in seconds
$OutputDir = "results/For_16x16"          # Output directory
```

### Bash (`run_multiple.sh`)

Edit the configuration section at the top:

```bash
# Configuration
NUM_RUNS=5
INSTANCES_ROOT="instances/16x16-database"
ALGORITHMS="0 3 4"
ANTS_SINGLE=10
ANTS_MULTI=3
NUM_ACS=2
NUM_COLONIES=3
THREADS=3
TIMEOUT=20
OUTPUT_DIR="results/For_16x16"
```

### Batch (`run_multiple.bat`)

Edit the configuration section at the top:

```bat
REM Configuration
set NUM_RUNS=5
set INSTANCES_ROOT=instances/16x16-database
set ALGORITHMS=0 3 4
set ANTS_SINGLE=10
set ANTS_MULTI=3
set NUM_ACS=2
set NUM_COLONIES=3
set THREADS=3
set TIMEOUT=20
set OUTPUT_DIR=results/For_16x16
```

---

## Example Configurations

### Example 1: 9x9 Puzzles (10 Runs)

**PowerShell:**
```powershell
$NumRuns = 10
$InstancesRoot = "instances/paquita-database"
$Algorithms = "0 3 4"
$AntsSingle = 5
$AntsMulti = 10
$Threads = 4
$Timeout = 10
$OutputDir = "results/For_9x9"
```

### Example 2: Quick Test (3 Runs, Single Instance)

**PowerShell:**
```powershell
$NumRuns = 3
$InstancesRoot = "instances/logic-solvable"
$Algorithms = "0"
$AntsSingle = 10
$Timeout = 5
$OutputDir = "results/Test"
```

### Example 3: Large Experiment (20 Runs)

**PowerShell:**
```powershell
$NumRuns = 20
$InstancesRoot = "instances/16x16-database"
$Algorithms = "0 2 3 4"
$AntsSingle = 10
$AntsMulti = 15
$Threads = 8
$Timeout = 60
$OutputDir = "results/Large_Experiment"
```

---

## Output

Each run creates a separate CSV file:

```
results/For_16x16/
├── Run_1.csv
├── Run_2.csv
├── Run_3.csv
├── Run_4.csv
└── Run_5.csv
```

Each CSV contains results for **all algorithms** specified in wide format:

```csv
puzzle_size,nAnts_alg0,nAnts_alg3,nAnts_alg4,time_mean_alg0,time_mean_alg3,time_mean_alg4,...
16x16,10,3,3,1.234567,2.345678,1.456789,...
```

---

## Console Output

The script provides progress updates:

```
================================================
Running solver 5 times
================================================

[1/5] Starting run 1...
Output: results/For_16x16/Run_1.csv

============================================================
Running Algorithm 0
============================================================
[alg 0] [1/100] instances/16x16-database/16x16_00001.txt -> OK (...)
...

[1/5] Run 1 completed successfully!

[2/5] Starting run 2...
Output: results/For_16x16/Run_2.csv
...

================================================
All runs completed!
Results saved in: results/For_16x16
================================================
```

---

## Execution Permissions

### Linux/Mac (Bash)

Make the script executable:

```bash
chmod +x scripts/run_multiple.sh
```

Then run:

```bash
./scripts/run_multiple.sh
```

### Windows (PowerShell)

If you get an execution policy error, run PowerShell as Administrator and execute:

```powershell
Set-ExecutionPolicy RemoteSigned
```

Then run the script normally.

---

## Tips

### 1. **Organize by Puzzle Size**

Create separate runs for different puzzle sizes:

```powershell
# Run 1: 9x9 puzzles
$OutputDir = "results/For_9x9"
$InstancesRoot = "instances/paquita-database"

# Run 2: 16x16 puzzles
$OutputDir = "results/For_16x16"
$InstancesRoot = "instances/16x16-database"
```

### 2. **Time Estimation**

Estimate total runtime:
```
Total Time ≈ (Number of Instances) × (Timeout) × (Number of Runs) × (Number of Algorithms)
```

Example:
```
100 instances × 20s timeout × 5 runs × 3 algorithms = 30,000 seconds ≈ 8.3 hours
```

### 3. **Background Execution**

**PowerShell (Windows):**
```powershell
Start-Job -FilePath .\scripts\run_multiple.ps1
```

**Bash (Linux/Mac):**
```bash
nohup bash scripts/run_multiple.sh > run_log.txt 2>&1 &
```

### 4. **Combining Results**

After all runs complete, you can analyze results across multiple CSVs:

```python
import pandas as pd

# Load all runs
runs = []
for i in range(1, 6):
    df = pd.read_csv(f'results/For_16x16/Run_{i}.csv')
    df['run'] = i
    runs.append(df)

# Combine
all_runs = pd.concat(runs)

# Analyze
print(all_runs.groupby('run')['time_mean_alg0'].mean())
```

---

## Troubleshooting

### Script doesn't run
- **Windows**: Check execution policy (see Execution Permissions)
- **Linux/Mac**: Ensure script has execute permissions (`chmod +x`)

### Python not found
- Ensure Python is in your PATH
- Try `python3` instead of `python` (Linux/Mac)

### Directory already exists error
- Script will use existing directory
- No error will occur

### Out of memory/disk space
- Reduce `$NumRuns`
- Use `--limit` in the Python command to process fewer instances
- Free up disk space

---

## See Also

- [RUN_GENERAL_GUIDE.md](../docs/RUN_GENERAL_GUIDE.md) - Complete guide for run_general.py
- [ANT_COUNT_PARAMETERS.md](../docs/ANT_COUNT_PARAMETERS.md) - Understanding ant count parameters
