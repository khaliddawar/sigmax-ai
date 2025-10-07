# PowerShell script to process the real meeting transcript with improved handling of large files

# Step 1: Create a temporary directory for our files (if it doesn't exist)
$tempDir = "scripts/temp"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
}

# Step 2: Create the JSON structure but with a placeholder for the transcript text
$metadata = @{
    title = "Macro Roadmap Trading Discussion"
    meeting_id = "macro-20250519"
    source = "manual"
} | ConvertTo-Json

# Step 3: Prepare the transcript to be sent separately as a file
$transcriptPath = "real_meeting.txt"
$outputJsonPath = "$tempDir/request.json"

# Step 4: Create our final payload using the -F operator to handle file content reading
$jsonTemplate = @"
{
    "transcript_id": "real_meeting_test",
    "transcript_text": $(Get-Content -Raw $transcriptPath | ConvertTo-Json),
    "metadata": $metadata
}
"@

# Step 5: Save the JSON to a file
$jsonTemplate | Out-File -FilePath $outputJsonPath -Encoding utf8

Write-Host "Created JSON payload file at $outputJsonPath"
Write-Host "Sending request to process transcript..."

# Step 6: Use the file directly in the request
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/transcripts" -Method POST -InFile $outputJsonPath -ContentType "application/json"
    Write-Host "Successfully processed transcript:" -ForegroundColor Green
    $response | ConvertTo-Json
    $transcriptId = $response.transcript_id
    Write-Host "Transcript ID: $transcriptId" -ForegroundColor Green
    
    # Save the transcript ID to use in subsequent requests
    $transcriptId | Out-File -FilePath "$tempDir/current_transcript_id.txt"
    Write-Host "Saved transcript ID to $tempDir/current_transcript_id.txt"
} catch {
    Write-Host "Error processing transcript:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "Response:" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $reader.DiscardBufferedData()
        $responseBody = $reader.ReadToEnd()
        Write-Host $responseBody -ForegroundColor Red
    }
}

Write-Host "Script completed." 