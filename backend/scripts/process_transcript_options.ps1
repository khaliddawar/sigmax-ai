# PowerShell script to process real_meeting.txt with multiple options
# This script lets you choose from different approaches to handle the large transcript

Write-Host "==== Transcript Processing Options ====" -ForegroundColor Cyan
Write-Host "This script provides multiple approaches to process the real_meeting.txt file" -ForegroundColor Cyan
Write-Host ""

Write-Host "Available methods:" -ForegroundColor Yellow
Write-Host "1. Standard PowerShell approach (original)" 
Write-Host "2. Improved PowerShell with file-based processing"
Write-Host "3. PowerShell with chunked file handling"
Write-Host "4. PowerShell with Base64 encoding (requires API support)"
Write-Host "5. Python approach (recommended)" 
Write-Host ""

$choice = Read-Host "Choose method (1-5)"

# Check that real_meeting.txt exists
if (-not (Test-Path "real_meeting.txt")) {
    Write-Host "Error: real_meeting.txt not found in current directory!" -ForegroundColor Red
    exit 1
}

# Create temp directory if it doesn't exist
$tempDir = "scripts/temp"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    Write-Host "Created temp directory: $tempDir" -ForegroundColor Green
}

switch ($choice) {
    "1" {
        Write-Host "Running original PowerShell script..." -ForegroundColor Yellow
        & "scripts/process_real_transcript.ps1"
    }
    "2" {
        Write-Host "Running improved PowerShell script..." -ForegroundColor Yellow
        & "scripts/process_real_transcript_improved.ps1"
    }
    "3" {
        Write-Host "Running chunked PowerShell script..." -ForegroundColor Yellow
        & "scripts/process_real_transcript_chunked.ps1"
    }
    "4" {
        Write-Host "Running Base64 PowerShell script..." -ForegroundColor Yellow
        Write-Host "WARNING: This requires a '/base64' endpoint on your API!" -ForegroundColor Red
        $confirm = Read-Host "Continue? (y/n)"
        if ($confirm -eq "y") {
            & "scripts/process_real_transcript_b64.ps1"
        } else {
            Write-Host "Cancelled." -ForegroundColor Yellow
        }
    }
    "5" {
        Write-Host "Running Python approach..." -ForegroundColor Yellow
        & "scripts/run_python_processor.ps1"
    }
    default {
        Write-Host "Invalid choice. Please run the script again and select 1-5." -ForegroundColor Red
    }
}

# After processing, check if we have a transcript ID
$idFiles = @(
    "scripts/temp/current_transcript_id.txt",
    "current_transcript_id.txt"
)

$foundId = $false
foreach ($idFile in $idFiles) {
    if (Test-Path $idFile) {
        $transcriptId = Get-Content -Raw $idFile
        $transcriptId = $transcriptId.Trim()
        Write-Host "`nTranscript processed! ID: $transcriptId" -ForegroundColor Green
        
        # Show example query command
        Write-Host "`nTo test Q&A with this transcript, run:" -ForegroundColor Yellow
        Write-Host 'Invoke-RestMethod -Uri "http://localhost:8001/api/qa" -Method POST -Body "{\\"transcript_id\\":\\"'$transcriptId'\\",\\"question\\":\\"What does Patrick expect for the S&P 500?\\"}" -ContentType "application/json"'
        
        $foundId = $true
        break
    }
}

if (-not $foundId) {
    Write-Host "`nNo transcript ID file found. Processing may have failed." -ForegroundColor Red
}

Write-Host "`nScript completed." -ForegroundColor Cyan 