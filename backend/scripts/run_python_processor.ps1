# PowerShell wrapper script to run the Python transcript processor
# This script activates the Python environment and runs the script

# Check if Python is installed
try {
    $pythonVersion = python --version
    Write-Host "Python found: $pythonVersion"
} catch {
    Write-Host "Error: Python not found. Please install Python 3.7 or newer." -ForegroundColor Red
    exit 1
}

# Check if our Python script exists
$pythonScript = "scripts/process_real_transcript.py"
if (-not (Test-Path $pythonScript)) {
    Write-Host "Error: Python script not found at $pythonScript" -ForegroundColor Red
    exit 1
}

Write-Host "Running Python script to process transcript..." -ForegroundColor Yellow

# Run the Python script
try {
    python $pythonScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Python script completed successfully!" -ForegroundColor Green
    } else {
        Write-Host "Python script failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    }
} catch {
    Write-Host "Error running Python script: $_" -ForegroundColor Red
    exit 1
}

# Check if we have a transcript ID file
$idFile = "scripts/temp/current_transcript_id.txt"
if (Test-Path $idFile) {
    $transcriptId = Get-Content -Raw $idFile
    $transcriptId = $transcriptId.Trim()
    Write-Host "Processed transcript ID: $transcriptId" -ForegroundColor Green
    
    # Provide command for testing the Q&A endpoint - simplified to avoid formatting issues
    Write-Host "`nTo test Q&A with this transcript, run:" -ForegroundColor Yellow
    Write-Host "Invoke-RestMethod -Uri 'http://localhost:8001/api/qa' -Method POST -ContentType 'application/json' -Body '{`"transcript_id`":`"$transcriptId`",`"question`":`"What does Patrick expect for the S&P 500?`"}'"
} else {
    Write-Host "No transcript ID file found. Processing may have failed." -ForegroundColor Red
}

Write-Host "Script completed." 