#!/usr/bin/env python3
"""
Combine multiple CSV runs into a single Excel file with multiple sheets.
Usage: python scripts/combine_to_excel.py --runs 5 --output results/combined.xlsx [other run_general.py args]
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_solver_multiple_times(num_runs: int, output_dir: Path, base_args: list) -> list:
    """Run run_general.py multiple times and return list of CSV file paths."""
    csv_files = []
    
    for i in range(1, num_runs + 1):
        csv_file = output_dir / f"Run_{i}.csv"
        
        print(f"\n{'='*60}")
        print(f"[{i}/{num_runs}] Starting run {i}...")
        print(f"Output: {csv_file}")
        print(f"{'='*60}\n")
        
        # Build command
        cmd = [sys.executable, "scripts/run_general.py"] + base_args + ["--output", str(csv_file)]
        
        # Run the command
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode == 0:
            print(f"\n[{i}/{num_runs}] Run {i} completed successfully!")
            csv_files.append(csv_file)
        else:
            print(f"\n[{i}/{num_runs}] Run {i} failed with exit code {result.returncode}")
        
    return csv_files


def combine_csvs_to_excel(csv_files: list, excel_output: Path):
    """Combine multiple CSV files into a single Excel file with multiple sheets."""
    import pandas as pd
    
    print(f"\n{'='*60}")
    print("Combining CSV files into Excel...")
    print(f"{'='*60}\n")
    
    with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
        for i, csv_file in enumerate(csv_files, start=1):
            if csv_file.exists():
                print(f"Adding sheet: Run_{i} from {csv_file}")
                df = pd.read_csv(csv_file)
                df.to_excel(writer, sheet_name=f"Run_{i}", index=False)
            else:
                print(f"Warning: {csv_file} not found, skipping...")
    
    print(f"\n{'='*60}")
    print(f"Excel file created: {excel_output}")
    print(f"Total sheets: {len(csv_files)}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run solver multiple times and combine results into Excel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run 5 times and combine into Excel
  python scripts/combine_to_excel.py --runs 5 --output results/combined.xlsx \\
      --instances-root instances/16x16-database --alg 0 2 3 4 \\
      --ants-single 10 --ants-multi 3 --threads 3 --timeout 20

  # Combine existing CSV files into Excel (no new runs)
  python scripts/combine_to_excel.py --combine-only --output results/combined.xlsx \\
      --csv-dir results/For_16x16
        """
    )
    
    parser.add_argument("--runs", type=int, default=5, 
                        help="Number of times to run the solver (default: 5)")
    parser.add_argument("--output", required=True, 
                        help="Output Excel file path (e.g., results/combined.xlsx)")
    parser.add_argument("--csv-dir", default=None,
                        help="Directory containing CSV files (for --combine-only mode)")
    parser.add_argument("--combine-only", action="store_true",
                        help="Only combine existing CSV files, don't run solver")
    parser.add_argument("--keep-csvs", action="store_true",
                        help="Keep temporary CSV files after combining (default: delete them)")
    
    # Parse known args to separate our args from run_general.py args
    args, unknown = parser.parse_known_args()
    
    # Validate
    excel_output = Path(args.output)
    if not excel_output.suffix == '.xlsx':
        print("Error: Output file must have .xlsx extension")
        return 1
    
    # Create output directory if needed
    excel_output.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if pandas and openpyxl are installed
    try:
        import pandas as pd
        import openpyxl
    except ImportError:
        print("Error: Required packages not installed.")
        print("Please install: pip install pandas openpyxl")
        return 1
    
    csv_files = []
    temp_dir = None
    
    if args.combine_only:
        # Combine existing CSV files
        if args.csv_dir is None:
            print("Error: --csv-dir required when using --combine-only")
            return 1
        
        csv_dir = Path(args.csv_dir)
        if not csv_dir.exists():
            print(f"Error: Directory not found: {csv_dir}")
            return 1
        
        # Find all Run_*.csv files
        csv_files = sorted(csv_dir.glob("Run_*.csv"))
        if not csv_files:
            print(f"Error: No Run_*.csv files found in {csv_dir}")
            return 1
        
        print(f"Found {len(csv_files)} CSV files to combine")
    else:
        # Run solver multiple times
        if not unknown:
            print("Error: No run_general.py arguments provided")
            print("Example: --instances-root instances/16x16-database --alg 0 2 3 4")
            return 1
        
        # Use a temporary directory for CSV files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = excel_output.parent / f"temp_csvs_{timestamp}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        csv_files = run_solver_multiple_times(args.runs, temp_dir, unknown)
    
    # Combine into Excel
    if csv_files:
        combine_csvs_to_excel(csv_files, excel_output)
        
        # Clean up temporary CSV files if requested
        if temp_dir and not args.keep_csvs:
            print(f"\nCleaning up temporary CSV files in {temp_dir}...")
            for csv_file in csv_files:
                if csv_file.exists():
                    csv_file.unlink()
            # Remove directory if empty
            try:
                temp_dir.rmdir()
                print("Temporary directory removed.")
            except:
                print(f"Note: Temporary directory {temp_dir} not empty, keeping it.")
        
        return 0
    else:
        print("Error: No CSV files to combine")
        return 1


if __name__ == "__main__":
    sys.exit(main())
