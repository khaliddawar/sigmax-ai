# PowerShell script using Base64 encoding to handle the real meeting transcript
# This approach avoids escaping issues with large text

# Create temp directory if needed
$tempDir = "scripts/temp"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
}

# Read the transcript file and convert to Base64
$transcriptPath = "real_meeting.txt"
$transcriptBytes = [System.IO.File]::ReadAllBytes($transcriptPath)
$transcriptBase64 = [Convert]::ToBase64String($transcriptBytes)

Write-Host "Read transcript file: $transcriptPath"
Write-Host "File size: $($transcriptBytes.Length) bytes"
Write-Host "Encoded as Base64"

# Create JSON payload with Base64-encoded transcript
$jsonPayload = @{
    transcript_id = "real_meeting_test"
    transcript_text_base64 = $transcriptBase64
    metadata = @{
        title = "Macro Roadmap Trading Discussion"
        meeting_id = "macro-20250519"
        source = "manual"
        encoding = "base64"
    }
} | ConvertTo-Json -Depth 10

# Save JSON to file
$jsonPath = "$tempDir/real_meeting_b64.json"
$jsonPayload | Out-File -FilePath $jsonPath -Encoding utf8

Write-Host "Created JSON payload file: $jsonPath"
Write-Host "Sending to API..."

# Send POST request
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/transcripts/base64" -Method POST -InFile $jsonPath -ContentType "application/json"
    
    Write-Host "Successfully processed transcript!" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Green
    $response | ConvertTo-Json
    
    # Save transcript ID
    if ($response.transcript_id) {
        $response.transcript_id | Out-File -FilePath "$tempDir/current_transcript_id.txt"
        Write-Host "Saved transcript ID to: $tempDir/current_transcript_id.txt" -ForegroundColor Green
    } else {
        Write-Host "No transcript ID in response" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error processing transcript:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.Exception.Response) {
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $reader.BaseStream.Position = 0
            $reader.DiscardBufferedData()
            $responseBody = $reader.ReadToEnd()
            Write-Host "Response details:" -ForegroundColor Red
            Write-Host $responseBody -ForegroundColor Red
        } catch {
            Write-Host "Could not read error response: $_" -ForegroundColor Red
        }
    }
}

Write-Host "Script completed."

# Note: For this approach to work, your API would need to handle a 'base64' endpoint
# that decodes the transcript_text_base64 field before processing 