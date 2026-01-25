@echo off
REM Batch script to run the solver multiple times
REM Usage: scripts\run_multiple.bat

REM Configuration
set NUM_RUNS=5
set INSTANCES_ROOT=instances/16x16-database
set ALGORITHMS=0 2 3 4
set ANTS_SINGLE=10
set ANTS_MULTI=3
set NUM_ACS=2
set NUM_COLONIES=3
set THREADS=3
set TIMEOUT=20
set OUTPUT_DIR=results/For_16x16

REM Create output directory if it doesn't exist
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
    echo Created directory: %OUTPUT_DIR%
)

echo ================================================
echo Running solver %NUM_RUNS% times
echo ================================================
echo.

REM Run the solver multiple times
for /L %%i in (1,1,%NUM_RUNS%) do (
    set OUTPUT_FILE=%OUTPUT_DIR%/Run_%%i.csv
    
    echo [%%i/%NUM_RUNS%] Starting run %%i...
    echo Output: %OUTPUT_DIR%/Run_%%i.csv
    
    python scripts/run_general.py ^
        --instances-root %INSTANCES_ROOT% ^
        --alg %ALGORITHMS% ^
        --ants-single %ANTS_SINGLE% ^
        --ants-multi %ANTS_MULTI% ^
        --numacs %NUM_ACS% ^
        --numcolonies %NUM_COLONIES% ^
        --threads %THREADS% ^
        --timeout %TIMEOUT% ^
        --output %OUTPUT_DIR%/Run_%%i.csv
    
    if errorlevel 1 (
        echo [%%i/%NUM_RUNS%] Run %%i failed!
    ) else (
        echo [%%i/%NUM_RUNS%] Run %%i completed successfully!
    )
    
    echo.
)

echo ================================================
echo All runs completed!
echo Results saved in: %OUTPUT_DIR%
echo ================================================
pause
