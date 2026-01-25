# PowerShell script to run the solver multiple times
# Usage: .\scripts\run_multiple.ps1

# Configuration
$NumRuns = 5
$InstancesRoot = "instances/16x16-database"
$Algorithms = "0 2 3 4"
$AntsSingle = 10
$AntsMulti = 3
$NumACS = 2
$NumColonies = 3
$Threads = 3
$Timeout = 20
$OutputDir = "results/For_16x16"

# Create output directory if it doesn't exist
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Created directory: $OutputDir"
}

Write-Host "================================================"
Write-Host "Running solver $NumRuns times"
Write-Host "================================================"
Write-Host ""

# Run the solver multiple times
for ($i = 1; $i -le $NumRuns; $i++) {
    $OutputFile = "$OutputDir/Run_$i.csv"
    
    Write-Host "[$i/$NumRuns] Starting run $i..."
    Write-Host "Output: $OutputFile"
    
    # Build the command
    $Command = "python scripts/run_general.py " +
               "--instances-root $InstancesRoot " +
               "--alg $Algorithms " +
               "--ants-single $AntsSingle " +
               "--ants-multi $AntsMulti " +
               "--numacs $NumACS " +
               "--numcolonies $NumColonies " +
               "--threads $Threads " +
               "--timeout $Timeout " +
               "--output $OutputFile"
    
    # Execute the command
    Invoke-Expression $Command
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[$i/$NumRuns] Run $i completed successfully!"
    } else {
        Write-Host "[$i/$NumRuns] Run $i failed with exit code $LASTEXITCODE"
    }
    
    Write-Host ""
}

Write-Host "================================================"
Write-Host "All runs completed!"
Write-Host "Results saved in: $OutputDir"
Write-Host "================================================"
