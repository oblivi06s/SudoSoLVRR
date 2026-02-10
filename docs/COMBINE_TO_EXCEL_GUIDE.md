# Combine to Excel Script Guide

## Overview

The `combine_to_excel.py` script runs the Sudoku solver multiple times and combines all results into a single Excel file with multiple sheets. This makes it easy to compare results across different runs in Excel.

## Prerequisites

Install required Python packages:

```bash
pip install pandas openpyxl
```

## Usage Modes

### Mode 1: Run and Combine (Default)

Run the solver N times and automatically combine results into Excel:

```bash
python scripts/combine_to_excel.py --runs 5 --output results/combined.xlsx \
    --instances-root instances/16x16-database \
    --alg 0 2 3 4 \
    --ants-single 10 --ants-multi 3 \
    --numacs 2 --numcolonies 3 --threads 3 \
    --timeout 20
```

**What happens:**
1. Creates temporary CSV files (Run_1.csv, Run_2.csv, etc.)
2. Runs `run_general.py` 5 times with your specified arguments
3. Combines all CSVs into a single Excel file with 5 sheets
4. Deletes temporary CSV files (unless `--keep-csvs` is used)

### Mode 2: Combine Only

Combine existing CSV files without running the solver:

```bash
python scripts/combine_to_excel.py --combine-only \
    --csv-dir results/For_16x16 \
    --output results/Combined_16x16.xlsx
```

**What happens:**
1. Finds all `Run_*.csv` files in the specified directory
2. Combines them into a single Excel file
3. Each CSV becomes a separate sheet (Run_1, Run_2, etc.)

## Arguments

### Required Arguments

- `--output PATH`: Output Excel file path (must end with `.xlsx`)

### Optional Arguments

- `--runs N`: Number of times to run the solver (default: 5)
- `--combine-only`: Only combine existing CSVs, don't run solver
- `--csv-dir PATH`: Directory containing CSV files (required with `--combine-only`)
- `--keep-csvs`: Keep temporary CSV files after combining (default: delete them)

### Pass-through Arguments

All other arguments are passed directly to `run_general.py`. See `RUN_GENERAL_GUIDE.md` for details.

## Examples

### Example 1: Run 9x9 puzzles 5 times

```bash
python scripts/combine_to_excel.py --runs 5 \
    --output results/Results_9x9.xlsx \
    --instances-root instances/paquita-database \
    --alg 0 3 4 \
    --ants-single 10 --ants-multi 3 \
    --numacs 2 --numcolonies 3 --threads 3 \
    --timeout 10
```

**Result:** `results/Results_9x9.xlsx` with 5 sheets (Run_1 through Run_5)

### Example 2: Run 16x16 puzzles 10 times

```bash
python scripts/combine_to_excel.py --runs 10 \
    --output results/Results_16x16.xlsx \
    --instances-root instances/16x16-database \
    --alg 0 2 3 4 \
    --ants-single 10 --ants-multi 3 \
    --numacs 2 --numcolonies 3 --threads 3 \
    --timeout 20
```

**Result:** `results/Results_16x16.xlsx` with 10 sheets

### Example 3: Combine existing results

If you already ran `run_multiple.bat` and have CSV files:

```bash
python scripts/combine_to_excel.py --combine-only \
    --csv-dir results/For_16x16 \
    --output results/For_16x16/Combined.xlsx
```

### Example 4: Keep temporary CSV files

```bash
python scripts/combine_to_excel.py --runs 3 \
    --output results/test.xlsx \
    --keep-csvs \
    --instances-root instances/paquita-database \
    --alg 0 3 4 \
    --ants-single 5 --ants-multi 2 \
    --timeout 5
```

**Result:** Excel file created AND temporary CSV files are kept

## Output Format

The Excel file contains:
- **Multiple sheets**: One sheet per run (Run_1, Run_2, Run_3, etc.)
- **Same columns**: All sheets have identical column structure from `run_general.py`
- **Easy comparison**: Open in Excel and compare results across sheets

### Excel Sheet Structure

Each sheet contains the same columns as the CSV output:
- `puzzle_size`
- `nAnts_alg0`, `nAnts_alg2`, `nAnts_alg3`, `nAnts_alg4`
- `threads_alg2`, `threads_alg4`
- `time_mean_alg0`, `time_mean_alg2`, etc.
- `cp_percentage_alg0`, `cp_percentage_alg2`, etc.
- And all other timing and performance metrics

## Tips

### 1. Analyzing Results in Excel

Once you have the Excel file:
- Use Excel's "Compare Sheets" feature
- Create pivot tables across multiple sheets
- Calculate averages across runs using formulas like `=AVERAGE(Run_1:Run_5!B2)`

### 2. Large Datasets

For large instance databases (e.g., 1000+ puzzles):
- Consider reducing `--runs` to 3 instead of 5
- Or use `--combine-only` mode to process results later

### 3. Naming Convention

Use descriptive names for output files:
```bash
--output results/9x9_alg034_5runs_$(date +%Y%m%d).xlsx
```

### 4. Batch Processing

Create a batch script to run multiple configurations:

```bash
# run_experiments.sh
for size in 9x9 16x16 25x25; do
    python scripts/combine_to_excel.py --runs 5 \
        --output results/Results_${size}.xlsx \
        --instances-root instances/${size}-database \
        --alg 0 2 3 4 \
        --ants-single 10 --ants-multi 3 \
        --timeout 20
done
```

## Troubleshooting

### Error: "Required packages not installed"

**Solution:** Install dependencies:
```bash
pip install pandas openpyxl
```

### Error: "No Run_*.csv files found"

**Solution:** Make sure you're pointing to the correct directory with `--csv-dir`

### Error: "Output file must have .xlsx extension"

**Solution:** Change your output filename to end with `.xlsx`:
```bash
--output results/combined.xlsx  # Correct
--output results/combined.csv   # Wrong
```

### Excel file is very large

**Solution:** Excel files are larger than CSV files. If size is an issue:
- Keep the CSV files instead of converting to Excel
- Or compress the Excel file: `zip results.zip results/combined.xlsx`

## Comparison with run_multiple Scripts

| Feature | `run_multiple.bat/ps1/sh` | `combine_to_excel.py` |
|---------|---------------------------|------------------------|
| Output format | Multiple CSV files | Single Excel file with multiple sheets |
| Easy comparison | Need to open multiple files | All data in one file |
| File size | Smaller (CSV) | Larger (Excel) |
| Excel compatibility | Need to import CSVs | Native Excel format |
| Flexibility | Fixed configuration | Can pass any arguments |
| Post-processing | Can combine later with `--combine-only` | N/A |

## See Also

- `RUN_GENERAL_GUIDE.md` - Complete guide for `run_general.py`
- `RUN_MULTIPLE_README.md` - Guide for `run_multiple` scripts
- `TIMING_DOCUMENTATION.md` - Understanding timing metrics
