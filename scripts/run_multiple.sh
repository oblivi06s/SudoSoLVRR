#!/bin/bash
# Bash script to run the solver multiple times
# Usage: bash scripts/run_multiple.sh

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

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo ""

echo "================================================"
echo "Running solver $NUM_RUNS times"
echo "================================================"
echo ""

# Run the solver multiple times
for i in $(seq 1 $NUM_RUNS); do
    OUTPUT_FILE="$OUTPUT_DIR/Run_$i.csv"
    
    echo "[$i/$NUM_RUNS] Starting run $i..."
    echo "Output: $OUTPUT_FILE"
    
    # Execute the command
    python scripts/run_general.py \
        --instances-root "$INSTANCES_ROOT" \
        --alg $ALGORITHMS \
        --ants-single $ANTS_SINGLE \
        --ants-multi $ANTS_MULTI \
        --numacs $NUM_ACS \
        --numcolonies $NUM_COLONIES \
        --threads $THREADS \
        --timeout $TIMEOUT \
        --output "$OUTPUT_FILE"
    
    if [ $? -eq 0 ]; then
        echo "[$i/$NUM_RUNS] Run $i completed successfully!"
    else
        echo "[$i/$NUM_RUNS] Run $i failed with exit code $?"
    fi
    
    echo ""
done

echo "================================================"
echo "All runs completed!"
echo "Results saved in: $OUTPUT_DIR"
echo "================================================"
