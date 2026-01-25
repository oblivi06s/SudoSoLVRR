# Combine to Excel - Quick Start

## Installation

```bash
pip install pandas openpyxl
```

## Quick Examples

### Run 5 times and combine to Excel

```bash
python scripts/combine_to_excel.py --runs 5 --output results/combined_1.xlsx \
    --instances-root instances/16x16-database \
    --alg 0 2 3 4 \
    --ants-single 10 --ants-multi 3 \
    --numacs 2 --numcolonies 3 --threads 3 \
    --timeout 20
```

### Combine existing CSV files

```bash
python scripts/combine_to_excel.py --combine-only \
    --csv-dir results/For_16x16 \
    --output results/Combined.xlsx
```

## What You Get

- **Single Excel file** with multiple sheets (Run_1, Run_2, Run_3, etc.)
- **Easy comparison** - all data in one place
- **Same format** as CSV output from `run_general.py`

## Key Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--runs N` | Number of times to run | `--runs 5` |
| `--output FILE` | Excel output file | `--output results/data.xlsx` |
| `--combine-only` | Only combine existing CSVs | `--combine-only` |
| `--csv-dir DIR` | Directory with CSV files | `--csv-dir results/For_16x16` |
| `--keep-csvs` | Don't delete temp CSVs | `--keep-csvs` |

All other arguments are passed to `run_general.py`.

## See Full Documentation

For complete details, see: `docs/COMBINE_TO_EXCEL_GUIDE.md`
